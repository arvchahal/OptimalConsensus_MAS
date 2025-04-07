#!/bin/bash

#######################
# 1. CONFIGURATION
#######################
NUM_AGENTS=1000
CONSENSUS_THRESHOLD=0.67
BYZANTINE_PERCENT=0.10 # 10% Byzantine agents
KAFKA_DIR=/usr/local/opt/kafka
CONSENSUS_LOG=logs/consensus.log
AGENT_LOG_DIR=logs/agents
PROPOSAL_METADATA=Block_A
BAD_PROPOSAL_METADATA=Block_BAD
TOPIC=votes
STAKE_FILE=agent_stakes.txt
EXPERIMENT_LOG=logs/experiment_results.log

# Setup logs
mkdir -p logs "$AGENT_LOG_DIR"
echo "" > "$STAKE_FILE"
echo "" > "$EXPERIMENT_LOG"

#######################
# 2. Start Kafka (macOS)
#######################
echo "Starting Kafka services..."
brew services start zookeeper
sleep 2
brew services start kafka
sleep 5

#######################
# 3. Create Kafka Topic
#######################
"$KAFKA_DIR/bin/kafka-topics.sh" --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --replication-factor 1 --partitions 1 --topic "$TOPIC"

#######################
# 4. Assign stakes and Byzantine agents
#######################
TOTAL_STAKE=0
declare -a STAKES=()
declare -a BYZANTINE_AGENTS=()

NUM_BYZANTINE=$(echo "$NUM_AGENTS * $BYZANTINE_PERCENT" | bc | awk '{print int($1+0.5)}')

echo "Launching $NUM_AGENTS agents ($NUM_BYZANTINE Byzantine agents)..."

for ((i=1; i<=NUM_AGENTS; i++)); do
  STAKE=$(( (RANDOM % 10) + 1 ))
  STAKES[$i]=$STAKE
  TOTAL_STAKE=$(( TOTAL_STAKE + STAKE ))

  # Save stake
  echo "$i $STAKE" >> "$STAKE_FILE"
done

# Randomly select Byzantine agents
BYZANTINE_AGENTS=($(shuf -i 1-"$NUM_AGENTS" -n "$NUM_BYZANTINE"))

echo "Byzantine Agents: ${BYZANTINE_AGENTS[*]}"
echo "Calculated TOTAL_STAKE=$TOTAL_STAKE"

#######################
# 5. Launch Consensus Listener
#######################
echo "Launching Consensus Listener..."
nohup python3 src/consensus.py "$CONSENSUS_THRESHOLD" "$TOTAL_STAKE" \
  > "$CONSENSUS_LOG" 2>&1 &

#######################
# 6. Spawn Agent Producers (Normal and Byzantine)
#######################
for ((i=1; i<=NUM_AGENTS; i++)); do
  STAKE_VALUE="${STAKES[$i]}"
  
  if [[ " ${BYZANTINE_AGENTS[@]} " =~ " $i " ]]; then
    # Byzantine agent votes incorrectly
    nohup python3 src/agent.py "$i" "$STAKE_VALUE" "$BAD_PROPOSAL_METADATA" --byz \
      > "$AGENT_LOG_DIR/agent_${i}_byzantine.log" 2>&1 &
  else
    # Normal agent votes correctly
    nohup python3 src/agent.py "$i" "$STAKE_VALUE" "$PROPOSAL_METADATA" \
      > "$AGENT_LOG_DIR/agent_${i}.log" 2>&1 &
  fi
done

echo "✅ All agents (normal & Byzantine) running."

#######################
# 7. Wait for Consensus Outcome
#######################
echo "Waiting for consensus result..."

TIME_START=$(date +%s)

TIMEOUT=300 # 5 minutes timeout to prevent infinite loop
SECONDS_ELAPSED=0

CONSENSUS_REACHED=false
while [[ $SECONDS_ELAPSED -lt $TIMEOUT ]]; do
  if grep -q "Consensus reached on proposal" "$CONSENSUS_LOG"; then
    CONSENSUS_REACHED=true
    break
  fi
  sleep 2
  SECONDS_ELAPSED=$(( $(date +%s) - TIME_START ))
done

TIME_END=$(date +%s)
TIME_TO_CONSENSUS=$((TIME_END - TIME_START))

if $CONSENSUS_REACHED; then
  echo "🎉 Consensus reached in $TIME_TO_CONSENSUS seconds."
  echo "SUCCESS $TIME_TO_CONSENSUS $NUM_AGENTS $NUM_BYZANTINE" >> "$EXPERIMENT_LOG"
else
  echo "❌ Consensus NOT reached in $TIME_TO_CONSENSUS seconds."
  echo "FAILURE $TIME_TO_CONSENSUS $NUM_AGENTS $NUM_BYZANTINE" >> "$EXPERIMENT_LOG"
fi

#######################
# 8. Shutdown Kafka
#######################
brew services stop kafka
brew services stop zookeeper

echo "Experiment complete."
