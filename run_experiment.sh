#!/bin/bash
set -e

###############################################################################
# 1. GLOBAL CONFIG
###############################################################################
NUM_AGENTS=10
CONSENSUS_THRESHOLD=0.67
BYZ_PCT=30              # 30 % byzantine in experiments 2‑3

BASE_DIR=logs
RESULTS=$BASE_DIR/results.txt
mkdir -p "$BASE_DIR"
: >"$RESULTS"

###############################################################################
# 2. HELPERS
###############################################################################
topic_cmd() { kafka-topics.sh --bootstrap-server localhost:9092 "$@"; }

reset_topics() {
  for t in election proposal votes; do topic_cmd --delete --topic "$t" 2>/dev/null || true; done
  sleep 2
  for t in election proposal votes; do topic_cmd --create --if-not-exists --replication-factor 1 --partitions 1 --topic "$t"; done
}

gen_stakes() {
  local stake_file=$1
  : >"$stake_file"
  TOTAL=0
  for ((i=1;i<=NUM_AGENTS;i++)); do
    v=$(( RANDOM % 10 + 1 ))
    eval STK_$i=$v
    TOTAL=$(( TOTAL + v ))
    echo "$i $v" >>"$stake_file"
  done
}

get_stake() {
  local i=$1
  eval echo "\$STK_$i"
}

launch_consensus() {
  local log_file=$1
  nohup python3 src/consensus.py "$CONSENSUS_THRESHOLD" "$TOTAL" >"$log_file" 2>&1 &
  sleep 1
}

spawn_agents() {
  local block=$1
  local log_dir=$2
  local byz_str="$3"
  for ((i=1;i<=NUM_AGENTS;i++)); do
    stake=$(get_stake $i)
    flag=""
    [[ $byz_str == *" $i "* ]] && flag="--byz"
    nohup python3 src/agent.py --id "$i" --stake "$stake" --proposal "$block" $flag       >"$log_dir/agent_${i}.log" 2>&1 &
  done
}

wait_cons() {
  local name=$1
  local log_file=$2
  start=$(date +%s)
  ok=false
  while (( $(date +%s) - start < 120 )); do
    grep -q "🏁" "$log_file" && { ok=true; break; }
    sleep 2
  done
  echo "$name : $ok" | tee -a "$RESULTS"
  pkill -P $$ python || true
  sleep 1
}

###############################################################################
# 3. START KAFKA ONCE
###############################################################################
brew services start zookeeper; sleep 2
brew services start kafka;     sleep 5
until nc -z localhost 9092; do sleep 1; done
echo "Kafka broker ready."

###############################################################################
# 4. EXPERIMENT 1 — all honest, Block_1
###############################################################################
echo "=== EXP 1: all honest, Block_1 ==="
EXP1_DIR=$BASE_DIR/exp1
mkdir -p "$EXP1_DIR"
reset_topics
gen_stakes "$EXP1_DIR/stakes.txt"
launch_consensus "$EXP1_DIR/consensus.log"
spawn_agents "Block_1" "$EXP1_DIR" ""
wait_cons "EXP1_all_honest" "$EXP1_DIR/consensus.log"

###############################################################################
# 5. EXPERIMENT 2 — 30 % byzantine followers voting BAD
###############################################################################
echo "=== EXP 2: byzantine followers vote BAD ==="
EXP2_DIR=$BASE_DIR/exp2
mkdir -p "$EXP2_DIR"
reset_topics
gen_stakes "$EXP2_DIR/stakes.txt"
BYZ_NUM=$(( NUM_AGENTS * BYZ_PCT / 100 ))
BYZ_IDS=$(shuf -i 1-"$NUM_AGENTS" -n "$BYZ_NUM" | tr '\n' ' ')
launch_consensus "$EXP2_DIR/consensus.log"
spawn_agents "Block_2" "$EXP2_DIR" "$BYZ_IDS"
wait_cons "EXP2_byz_followers" "$EXP2_DIR/consensus.log"

###############################################################################
# 6. EXPERIMENT 3 — byzantine leader proposes Block_3_BAD
###############################################################################
echo "=== EXP 3: byzantine leader Block_3_BAD ==="
EXP3_DIR=$BASE_DIR/exp3
mkdir -p "$EXP3_DIR"
reset_topics
gen_stakes "$EXP3_DIR/stakes.txt"
LEADER_BYZ=$(shuf -i 1-"$NUM_AGENTS" -n 1)
launch_consensus "$EXP3_DIR/consensus.log"
spawn_agents "Block_3_BAD" "$EXP3_DIR" "$LEADER_BYZ"
wait_cons "EXP3_byz_leader" "$EXP3_DIR/consensus.log"

###############################################################################
# 9. CLEAN SHUTDOWN
###############################################################################
brew services stop kafka
brew services stop zookeeper
echo "All experiments complete.  Results in $RESULTS"
