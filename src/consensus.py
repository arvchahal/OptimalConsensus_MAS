# consensus.py
import sys
from kafka import KafkaConsumer
import json
from transaction import Transaction
from security import verify_signature, generate_keys

class Consensus:
    def __init__(self, threshold, total_weight):
        self.threshold = threshold
        self.total = total_weight
        self.votes = {}
        self.public_key, self.private_key = generate_keys()

    def register_vote(self, proposal, weight):
        if proposal in self.votes:
            self.votes[proposal] += weight
        else:
            self.votes[proposal] = weight

    def check_consensus(self):
        for proposal, weight in self.votes.items():
            if weight / self.total >= self.threshold:
                return proposal
        return None

    def listen(self):
        consumer = KafkaConsumer(
            'votes',
            bootstrap_servers='localhost:9092',
            group_id='consensus',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )

        print("Listening for votes...")
        for msg in consumer:
            vote = msg.value

            # Rebuild proposal
            proposal = Transaction(
                vote['proposal']['proposer'],
                vote['proposal']['action'],
                vote['proposal']['metadata'],
                vote['proposal']['timestamp']
            )
            proposal.signature = bytes.fromhex(vote['proposal']['signature'])
            proposal.public_key = vote['proposal']['public_key'].encode()

            proposal_valid = proposal.verify_signature(proposal.public_key)
            vote_message = f"{vote['agent_id']}:{vote['proposal']['metadata']}"
            vote_valid = verify_signature(
                vote_message,
                bytes.fromhex(vote['vote_signature']),
                vote['voter_pub_key'].encode()
            )

            if proposal_valid and vote_valid:
                self.register_vote(vote['proposal']['metadata'], vote['weight'])
                print(f"✅ Accepted vote: {vote}")
            else:
                print(f"❌ Rejected vote: {vote}")

            winner = self.check_consensus()
            if winner:
                print(f"\\n🏁 Consensus reached on proposal: {winner}")
                break

if __name__ == "__main__":
    # Parse threshold + total stake
    threshold = float(sys.argv[1])  # e.g. 0.67
    total_stake = int(sys.argv[2])  # sum of agent stakes

    consensus = Consensus(threshold, total_stake)
    consensus.listen()