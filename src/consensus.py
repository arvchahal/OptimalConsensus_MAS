# src/consensus.py
import json
import sys
import time
from kafka import KafkaConsumer, KafkaProducer
import threading
from stake import Stake
from transaction import Transaction
from security import verify_signature, generate_keys


class Consensus:
    """
    Proof‑of‑Stake consensus with:
      1) leader elected by stake‑weighted lottery
      2) leader publishes PROPOSE_BLOCK on 'proposal' topic
      3) validators vote on 'votes' topic
      4) slashing for bad behaviour
    """

    def __init__(self, threshold, total_weight, stake_system: Stake):
        self.threshold = threshold
        self.total = total_weight
        self.stake_system = stake_system

        # live state
        self.current_round = 0
        self.leader_id = None
        self.current_proposal = None
        self.votes = {}         # proposal → accumulated weight
        self.bad_votes = {}     # agent_id → count

        # keys only used if this node ever signs something
        self.public_key, self.private_key = generate_keys()

        # one producer to broadcast election result (optional) & misc
        self.producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode(),
        )

    # --------------------------------------------------------------------- #
    #  Round control                                                         #
    # --------------------------------------------------------------------- #
    def start_round(self):
        """Elect a leader and broadcast the result."""
        self.current_round += 1
        self.votes.clear()
        self.current_proposal = None

        self.leader_id = self.stake_system.pick_leader()
        election_msg = {"round": self.current_round, "leader_id": self.leader_id}

        def _broadcast_election():
            for _ in range(5):          # 5 seconds of retries
                self.producer.send("election", election_msg)
                self.producer.flush()
                time.sleep(1)
        threading.Thread(target=_broadcast_election, daemon=True).start()
        print(f"🗳  Round {self.current_round}: elected leader Agent {self.leader_id}")

    # --------------------------------------------------------------------- #
    #  Main event loop                                                      #
    # --------------------------------------------------------------------- #
    def listen(self):
        consumer = KafkaConsumer(
            "proposal",
            "votes",
            bootstrap_servers="localhost:9092",
            group_id="consensus",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
        )

        print("Consensus engine online …")
        self.start_round()

        for record in consumer:
            topic = record.topic
            msg = record.value

            if topic == "proposal":
                self._handle_proposal(msg)
            elif topic == "votes":
                self._handle_vote(msg)

            # after every event, see if someone has crossed the threshold
            winner = self.check_consensus()
            if winner:
                print(f"🏁 Round {self.current_round}: consensus on {winner}\n")
                self.start_round()          # begin next height immediately

    # --------------------------------------------------------------------- #
    #  Proposal handling                                                    #
    # --------------------------------------------------------------------- #
    def _handle_proposal(self, proposal_dict):
        proposer_id = proposal_dict["proposer"]

        if proposer_id != self.leader_id:
            print(f"❌ Non‑leader proposal from Agent {proposer_id} — slashing")
            self._slash_bad_vote(proposer_id)
            return

        # (Optional) verify leader’s signature on the proposal here

        self.current_proposal = proposal_dict["metadata"]
        print(f"[ROUND {self.current_round}] tracking proposal = {self.current_proposal}")
        print(f"📦  Leader Agent {proposer_id} proposed block: {self.current_proposal}")

    # --------------------------------------------------------------------- #
    #  Vote handling (same checks you had, just moved)                      #
    # --------------------------------------------------------------------- #
    def _handle_vote(self, vote_msg):
        if self.current_proposal is None:
            print('no prposal')
            return 
        else:
            print(self.current_proposal)
        agent_id = vote_msg["id"]
        weight = vote_msg["weight"]
        vote_signature_hex = vote_msg["vote_signature"]
        voter_pub_key_str = vote_msg["voter_pub_key"]

        # --- rebuild proposal embedded in the vote (unchanged logic) ------
        proposal_dict = vote_msg["proposal"]
        proposal_tx = Transaction(
            proposer=proposal_dict["proposer"],
            action=proposal_dict["action"],
            metadata=proposal_dict["metadata"],
            timestamp=proposal_dict["timestamp"],
        )
        proposal_tx.signature = bytes.fromhex(proposal_dict["signature"])
        proposal_tx.public_key = proposal_dict["public_key"].encode()

        proposal_valid = proposal_tx.verify_signature(proposal_tx.public_key)

        vote_str = f"{agent_id}:{proposal_dict['metadata']}"
        vote_valid = verify_signature(
            vote_str,
            bytes.fromhex(vote_signature_hex),
            voter_pub_key_str.encode(),
        )

        candidate = proposal_dict["metadata"]
        if (
            proposal_valid
            and vote_valid
            and self.current_proposal
            and candidate == self.current_proposal
        ):
            reward_amt = self.stake_system.reward(agent_id, 0.01)
            print(
                f"✅ Accepted vote from Agent {agent_id}: +{reward_amt} stake (weight {weight})"
            )
            self.register_vote(candidate, weight)
        else:
            print(f"❌ Bad vote from Agent {agent_id} — slashing")
            self._slash_bad_vote(agent_id)
        print(f"[DEBUG] {agent_id} voted {candidate}, weight={weight}")

    # --------------------------------------------------------------------- #
    #  Helpers                                                              #
    # --------------------------------------------------------------------- #
    def register_vote(self, candidate, weight):
        self.votes[candidate] = self.votes.get(candidate, 0) + weight

    def check_consensus(self):
        for candidate, wt in self.votes.items():
            if wt >= self.threshold * self.total:
                return candidate
        return None

    def _slash_bad_vote(self, agent_id):
        amount = self.stake_system.slash(agent_id, 0.05)  # 5 % penalty
        self.bad_votes[agent_id] = self.bad_votes.get(agent_id, 0) + 1
        with open("logs/slashing.log", "a") as f:
            f.write(f"{time.time():.0f} Agent {agent_id} slashed {amount}\n")


# ------------------------------------------------------------------------- #
#  Program entry                                                            #
# ------------------------------------------------------------------------- #
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python consensus.py <threshold> <total_stake>")
        sys.exit(1)

    threshold = float(sys.argv[1])
    total_stake = int(sys.argv[2])

    stake_sys = Stake()

    # read stakes from file
    with open("agent_stakes.txt") as fh:
        for ln in fh:
            if ln.strip():
                aid, amt = ln.split()
                stake_sys.stake(int(aid), int(amt))

    consensus = Consensus(threshold, total_stake, stake_sys)
    consensus.listen()
