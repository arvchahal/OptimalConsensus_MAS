from kafka import KafkaConsumer
import sys
import json
from transaction import Transaction
from security import verify_signature, generate_keys
from vote import Vote  # if you need to instantiate a Vote object
                      # for more detailed validation

class Consensus:
    """Implements a probabilistic PoS voting consensus with slashing."""
    def __init__(self, threshold, total_weight, stake_system=None):
        """
        :param threshold: e.g., 0.67 for 67% threshold
        :param total_weight: total vote weight (sum of stakes for validators)
        :param stake_system: reference to Stake system for slashing
        """
        self.threshold = threshold
        self.total = total_weight
        self.votes = {}  # map {proposal_string: accumulated_weight}
        self.public_key, self.private_key = generate_keys()

        # From slashing side
        self.stake_system = stake_system
        self.current_proposal = None
        self.bad_votes = {}  # tracking number of bad votes per agent

    def set_current_proposal(self, proposal_str):
        """Set the current proposal being voted on (string or ID)."""
        self.current_proposal = proposal_str

    def listen(self):
        """
        Consume votes from Kafka and handle them.
        If a vote is valid, add its weight.
        If invalid, slash the voter's stake.
        """
        consumer = KafkaConsumer(
            'votes',
            bootstrap_servers='localhost:9092',
            group_id='consensus',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )

        print("Listening for votes...")
        for msg in consumer:
            vote_msg = msg.value
            # This dictionary should contain:
            # {
            #   "agent_id": ...,
            #   "proposal": {...},
            #   "vote_signature": ...,
            #   "voter_pub_key": ...,
            #   "weight": ...
            # }
            agent_id = vote_msg["agent_id"]
            weight = vote_msg["weight"]
            vote_signature_hex = vote_msg["vote_signature"]
            voter_pub_key_str = vote_msg["voter_pub_key"]

            # Rebuild the proposal as a Transaction to verify its signature
            proposal_dict = vote_msg["proposal"]
            proposal_tx = Transaction(
                proposer=proposal_dict["proposer"],
                action=proposal_dict["action"],
                metadata=proposal_dict["metadata"],
                timestamp=proposal_dict["timestamp"]
            )
            proposal_tx.signature = bytes.fromhex(proposal_dict["signature"])
            proposal_tx.public_key = proposal_dict["public_key"].encode()

            # 1. Check proposal validity
            proposal_valid = proposal_tx.verify_signature(proposal_tx.public_key)

            # 2. Check vote validity (signature matches "agent_id:metadata")
            vote_str = f"{agent_id}:{proposal_dict['metadata']}"
            vote_valid = verify_signature(
                vote_str,
                bytes.fromhex(vote_signature_hex),
                voter_pub_key_str.encode()
            )

            # Optionally, also check if agent is voting for the *current_proposal* if set
            # e.g. if self.current_proposal is a string "Block_A"
            # and we expect that metadata to match.
            # We'll unify everything in a single "register_vote" call:
            if proposal_valid and vote_valid:
                # all checks pass => register the vote
                candidate = proposal_dict["metadata"]
                self.register_vote(candidate, agent_id, weight,
                                   signature=vote_signature_hex,
                                   public_key=voter_pub_key_str)
                print(f"✅ Accepted vote from Agent {agent_id}: {vote_msg}")
            else:
                # One or both checks failed => slash
                self._slash_bad_vote(agent_id)
                print(f"❌ Rejected vote from Agent {agent_id}: {vote_msg}")

            # Check if consensus is reached
            winner = self.check_consensus()
            if winner:
                print(f"\n🏁 Consensus reached on proposal: {winner}")
                break

    def register_vote(self, candidate, voter_id, weight=1, signature=None, public_key=None):
        """
        Extended from 'slashing' side: If we want to do an additional check or record data.
        Currently, we assume the big validations happened in `listen()`, but we can do more checks here if desired.
        """
        # If we want to create a 'Vote' object for further checks:
        # vote_obj = Vote(voter_id, candidate)
        # vote_obj.signature = bytes.fromhex(signature)  # etc.

        if candidate in self.votes:
            self.votes[candidate] += weight
        else:
            self.votes[candidate] = weight
        return True

    def _verify_vote(self, vote_obj, voter_id, public_key):
        """
        Slashing side approach: If you want to unify an actual 'Vote' object approach.
        Right now, we do simpler checks in `listen()`.
        """
        print(f"DEBUG: Verifying vote from Agent {voter_id}")
        sig_valid = vote_obj.verify_signature(public_key)
        if not sig_valid:
            print(f"DEBUG: Signature verification failed for Agent {voter_id}")
            return False
        if self.current_proposal and vote_obj.proposal_id != self.current_proposal:
            print(f"DEBUG: Agent {voter_id} voted for wrong proposal. "
                  f"Expected: {self.current_proposal}, Got: {vote_obj.proposal_id}")
            return False
        print(f"DEBUG: Vote from Agent {voter_id} is valid")
        return True

    def _slash_bad_vote(self, agent_id):
        """
        If a vote is found invalid, slash the agent's stake (5% penalty).
        """
        if self.stake_system:
            slash_amount = self.stake_system.slash(agent_id, 0.05)  # 5% penalty
            print(f"Agent {agent_id} slashed {slash_amount} stake for bad vote.")
        else:
            print(f"(No stake system) Would slash agent {agent_id}")

        # Track # of bad votes
        if agent_id not in self.bad_votes:
            self.bad_votes[agent_id] = 0
        self.bad_votes[agent_id] += 1

    def check_consensus(self):
        """
        Checks if any proposal's weighted votes >= threshold * total_stake.
        """
        for proposal, vote_count in self.votes.items():
            if vote_count / self.total >= self.threshold:
                return proposal
        return None


if __name__ == "__main__":
    # E.g. usage: python consensus.py 0.67 100
    threshold = float(sys.argv[1])
    total_stake = int(sys.argv[2])

    # If you have a stake system, pass it in. For example:
    # from stake import Stake
    # stake_system = Stake()
    # consensus = Consensus(threshold, total_stake, stake_system)
    # But if not, just do:
    consensus = Consensus(threshold, total_stake)
    consensus.listen()
