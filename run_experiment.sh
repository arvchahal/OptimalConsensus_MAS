#!/bin/bash
###############################################################################
# 1. CONFIGURATION
###############################################################################
NUM_AGENTS=100
CONSENSUS_THRESHOLD=0.67
BYZANTINE_PERCENT=0.30       # 30 % Byzantine agents

KAFKA_DIR=/usr/local/opt/kafka        # adjust if `kafka-topics.sh` lives elsewhere
CONSENSUS_LOG=logs/consensus.log
AGENT_LOG_DIR=logs/agents

STAKE_FILE=agent_stakes.txt
EXPERIMENT_LOG=logs/experiment_results.log

###############################################################################
# 2. LOG SETUP
###############################################################################
mkdir -p logs "$AGENT_LOG_DIR"
: > "$STAKE_FILE"
: > "$EXPERIMENT_LOG"

###############################################################################
# 3. START KAFKA (macOS Homebrew install)
###############################################################################
echo "Starting Kafka services..."
brew services start zookeeper
sleep 2
brew services start kafka
sleep 5

echo "Waiting for broker on :9092 ..."
until nc -z localhost 9092; do sleep 1; done
echo "Kafka broker is up."

###############################################################################
# 4. CREATE TOPICS (votes / proposal / election)
###############################################################################
for TOPIC in votes proposal election; do
  "$KAFKA_DIR/bin/kafka-topics.sh" --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 --partitions 1 --topic "$TOPIC" \
    || { echo "❌ Failed to create topic $TOPIC"; exit 1; }
done

###############################################################################
# 5. ASSIGN STAKES & PICK BYZANTINE AGENTS
###############################################################################
TOTAL_STAKE=0
declare -a STAKES          # 1‑indexed for convenience
declare -a BYZANTINE_AGENTS

NUM_BYZANTINE=$(echo "$NUM_AGENTS * $BYZANTINE_PERCENT" | bc | awk '{print int($1+0.5)}')

echo "Launching $NUM_AGENTS agents ($NUM_BYZANTINE Byzantine)…"

for ((i=1; i<=NUM_AGENTS; i++)); do
  STAKE=$(( (RANDOM % 10) + 1 ))
  STAKES[$i]=$STAKE
  TOTAL_STAKE=$(( TOTAL_STAKE + STAKE ))
  echo "$i $STAKE" >> "$STAKE_FILE"
done

BYZANTINE_AGENTS=($(shuf -i 1-"$NUM_AGENTS" -n "$NUM_BYZANTINE"))

echo "Byzantine  : ${BYZANTINE_AGENTS[*]}"
echo "TOTAL_STAKE: $TOTAL_STAKE"

###############################################################################
# 6. LAUNCH CONSENSUS LISTENER
###############################################################################
echo "Launching Consensus Listener…"
nohup python3 src/consensus.py "$CONSENSUS_THRESHOLD" "$TOTAL_STAKE" \
      > "$CONSENSUS_LOG" 2>&1 &

###############################################################################
# 7. SPAWN AGENTS
###############################################################################
for ((i=1; i<=NUM_AGENTS; i++)); do
  STAKE_VALUE="${STAKES[$i]}"
  EXTRA_FLAG=""
  if [[ " ${BYZANTINE_AGENTS[*]} " =~ " $i " ]]; then
    EXTRA_FLAG="--byz"
  fi
  nohup python3 src/agent.py --id "$i" --stake "$STAKE_VALUE" $EXTRA_FLAG \
       > "$AGENT_LOG_DIR/agent_${i}.log" 2>&1 &
done
echo "✅ All agents started."

###############################################################################
# 8. WAIT FOR CONSENSUS RESULT (first round only)
###############################################################################
echo "Waiting for first consensus…"
START_TIME=$(date +%s)
TIMEOUT=300       # seconds
CONSENSUS_REACHED=false

while (( $(date +%s) - START_TIME < TIMEOUT )); do
  if grep -q "🏁 Round" "$CONSENSUS_LOG"; then
    CONSENSUS_REACHED=true
    break
  fi
  sleep 2
done

ELAPSED=$(( $(date +%s) - START_TIME ))

if $CONSENSUS_REACHED; then
  echo "🎉 Consensus reached in $ELAPSED s."
  echo "SUCCESS $ELAPSED $NUM_AGENTS $NUM_BYZANTINE" >> "$EXPERIMENT_LOG"
else
  echo "❌ No consensus within $ELAPSED s."
  echo "FAILURE $ELAPSED $NUM_AGENTS $NUM_BYZANTINE" >> "$EXPERIMENT_LOG"
fi

###############################################################################
# 9. CLEAN SHUTDOWN
###############################################################################
brew services stop kafka
brew services stop zookeeper
echo "Experiment complete."
