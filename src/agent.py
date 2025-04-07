from kafka import KafkaProducer
import json
import random
import sys
import time
import argparse
import datetime

from security import generate_keys, sign_message
from transaction import Transaction

# If you have a separate 'vote.py' or 'Vote' class, you can import it here:
# from vote import Vote


class Agent:
    def __init__(self, agent_id, stake, is_byzantine):
        self.agent_id = agent_id
        self.stake = stake
        self.is_byzantine = is_byzantine

        # Additional fields from the “slashing” side
        self.decisions = []  # placeholder for internal decisions
        self.is_leader = False

        # Generate keys for signing proposals/votes
        self.private_key, self.public_key = generate_keys()

        # Kafka Producer
        self.producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=30000,   # 30s
            delivery_timeout_ms=60000   # 60s
        )

    # ----------------------
    # Methods from “slashing” side
    # ----------------------

    def propose_legacy(self):
        """
        For simplicity, generate a 'legacy' style proposal (a block) as a string.
        Retained from 'slashing' branch in case you still want to use it.
        """
        proposal = f"Block proposed by Agent {self.agent_id}: {random.randint(1,100)}"
        return proposal

    def create_valid_vote_obj(self, proposal_str):
        """
        Create a valid Vote object for the given proposal string (if using vote.py).
        """
        from vote import Vote
        vote = Vote(self.agent_id, proposal_str)
        vote.sign_transaction(self.private_key)
        return vote

    def create_bad_vote_obj(self, proposal_str):
        """
        Create an invalid Vote object with a corrupted signature or wrong proposal.
        """
        from vote import Vote
        import random
        bad_type = random.choice(["wrong_signature", "wrong_proposal", "stale_timestamp"])

        vote = Vote(self.agent_id, proposal_str)
        if bad_type == "wrong_signature":
            # Corrupt the metadata before signing
            vote.metadata["corrupted"] = "yes"
            vote.sign_transaction(self.private_key)
            # Remove the corruption post-sign -> signature mismatch
            vote.metadata.pop("corrupted")

        elif bad_type == "wrong_proposal":
            # Vote for a different fake proposal
            fake_proposal = f"Fake proposal: {random.randint(1000, 9999)}"
            vote = Vote(self.agent_id, fake_proposal)
            vote.sign_transaction(self.private_key)

        elif bad_type == "stale_timestamp":
            # Set timestamp to 10 minutes ago
            vote.timestamp = time.time() - 600
            vote.sign_transaction(self.private_key)

        return vote

    # ----------------------
    # Methods from “main” side
    # ----------------------

    def create_proposal(self):
        """
        Create and sign a proposal Transaction with a timezone-aware timestamp.
        This is your primary method for a real consensus flow.
        """
        tx = Transaction(
            proposer=self.agent_id,
            action="PROPOSE_BLOCK",
            metadata="Block_A",
            timestamp=str(datetime.datetime.now(datetime.timezone.utc))
        )
        tx.sign_transaction(self.private_key)
        return tx

    def vote(self, proposal):
        """
        Verifies the proposal's signature, then signs a 'vote' message and publishes to Kafka.
        """
        # Validate the proposal
        if not proposal.verify_signature(proposal.public_key):
            print(f"Agent {self.agent_id}: Invalid proposal signature. Rejecting.")
            return

        message = f"{self.agent_id}:{proposal.metadata}"
        vote_signature = sign_message(message, self.private_key)

        vote_dict = {
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
        self.producer.send("votes", vote_dict)
        print(f"Agent {self.agent_id} published vote: {vote_dict}")

    def shutdown(self):
        """
        Flush and close the Kafka producer to avoid KafkaTimeoutError on process exit.
        """
        try:
            self.producer.flush()
            self.producer.close()
        except Exception as e:
            print(f"Error while closing producer: {e}")

# ----------------------
# Command-Line Entry Point
# ----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_id", type=int)
    parser.add_argument("stake", type=int)
    parser.add_argument("proposal_metadata")
    parser.add_argument("--byz", action="store_true")
    args = parser.parse_args()

    agent = Agent(args.agent_id, args.stake, args.byz)
    time.sleep(args.agent_id)  # Stagger votes

    # Use the "main" style proposal
    proposal = agent.create_proposal()
    # Attach agent's pubkey to the proposal so other nodes can verify
    proposal.public_key = agent.public_key

    # Agent creates and sends a vote for that proposal
    agent.vote(proposal)

    # Give Kafka some time to send
    time.sleep(1)
    # Graceful shutdown
    agent.shutdown()
