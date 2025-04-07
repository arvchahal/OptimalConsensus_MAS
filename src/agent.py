from kafka import KafkaProducer
import json
import random
import sys
import time
import argparse
from transaction import Transaction
from security import generate_keys, sign_message
import datetime

class Agent:
    def __init__(self, agent_id, stake, is_byzantine):
        self.agent_id = agent_id
        self.stake = stake
        self.is_byzantine = is_byzantine
        self.private_key, self.public_key = generate_keys()
        self.producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # Increase timeouts if needed:
            request_timeout_ms=30000,    # 30s
            delivery_timeout_ms=60000    # 60s
        )

    def create_proposal(self):
        """
        Create and sign a proposal transaction with a timezone-aware timestamp.
        """
        tx = Transaction(
            proposer=self.agent_id,
            action="PROPOSE_BLOCK",
            metadata="Block_A",
            # Use timezone-aware current time
            timestamp=str(datetime.datetime.now(datetime.timezone.utc))
        )
        tx.sign_transaction(self.private_key)
        return tx

    def vote(self, proposal):
        # Validate the proposal before voting
        if not proposal.verify_signature(proposal.public_key):
            print(f"Agent {self.agent_id}: Invalid proposal signature. Rejecting.")
            return

        message = f"{self.agent_id}:{proposal.metadata}"
        vote_signature = sign_message(message, self.private_key)

        vote = {
            "agent_id": self.agent_id,
            "proposal": {
                "proposer": proposal.proposer,
                "action": proposal.action,
                "metadata": proposal.metadata,
                "timestamp": proposal.timestamp,
                "signature": proposal.signature.hex(),
                "public_key": proposal.public_key.decode()
            },
            "vote_signature": vote_signature.hex(),
            "voter_pub_key": self.public_key.decode(),
            "weight": self.stake
        }

        # Publish vote
        self.producer.send("votes", vote)
        print(f"Agent {self.agent_id} published vote: {vote}")

    def shutdown(self):
        """
        Gracefully flush and close the Kafka producer to avoid KafkaTimeoutError at exit.
        """
        try:
            self.producer.flush()
            self.producer.close()
        except Exception as e:
            print(f"Error while closing producer: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_id", type=int)
    parser.add_argument("stake", type=int)
    parser.add_argument("proposal_metadata")
    parser.add_argument("--byz", action="store_true")
    args = parser.parse_args()

    agent = Agent(args.agent_id, args.stake, args.byz)
    time.sleep(args.agent_id)  # stagger votes

    proposal = agent.create_proposal()
    proposal.public_key = agent.public_key  # Attach for broadcast
    agent.vote(proposal)

    # Give Kafka a little time to send
    time.sleep(1)

    # Ensure the producer finishes in-flight messages
    agent.shutdown()
