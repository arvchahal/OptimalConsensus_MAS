#!/bin/bash

#######################
# 1. CONFIG
#######################
NUM_AGENTS=1000
CONSENSUS_THRESHOLD=0.67
KAFKA_DIR=/usr/local/opt/kafka   # If using Homebrew Kafka
CONSENSUS_LOG=logs/consensus.log
AGENT_LOG_DIR=logs/agents
PROPOSAL_METADATA=Block_A
TOPIC=votes

# Create logs folder
mkdir -p logs
mkdir -p "$AGENT_LOG_DIR"

#######################
# 2. Start Kafka (macOS)
#######################
echo "Starting Zookeeper and Kafka..."
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
# 4. Calculate total stake & spawn agents
#######################
TOTAL_STAKE=0
declare -a STAKES=()

echo "Launching $NUM_AGENTS agents..."
for ((i=1; i<=NUM_AGENTS; i++)); do
  # Restrict each agent's stake to 1..10
  STAKE=$(( (RANDOM % 10) + 1 ))
  STAKES[$i]=$STAKE
  TOTAL_STAKE=$(( TOTAL_STAKE + STAKE ))
done

echo "Calculated TOTAL_STAKE=$TOTAL_STAKE"

#######################
# 5. Start Consensus Listener
#######################
echo "Launching Consensus Listener..."
nohup python3 src/consensus.py "$CONSENSUS_THRESHOLD" "$TOTAL_STAKE" \
  > "$CONSENSUS_LOG" 2>&1 &

#######################
# 6. Spawn Agents (in background)
#######################
for ((i=1; i<=NUM_AGENTS; i++)); do
  STAKE_VALUE="${STAKES[$i]}"
  nohup python3 src/agent.py "$i" "$STAKE_VALUE" "$PROPOSAL_METADATA" \
    > "$AGENT_LOG_DIR/agent_$i.log" 2>&1 &
done

echo "✅ All agents and consensus are now running in the background."

#######################
# 7. Wait for Consensus
#######################
echo "Waiting for consensus to be reached..."

while ! grep -q "Consensus reached on proposal" "$CONSENSUS_LOG"; do
  sleep 2
done

echo "🎉 Consensus has been reached! Exiting script."
