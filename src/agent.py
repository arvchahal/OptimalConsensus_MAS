#!/usr/bin/env python3
"""
Agent process for the PoS demo.

Honest validator:
    python3 agent.py --id 7 --stake 5 --proposal Block_A

Byzantine validator (still just votes Block_BAD):
    python3 agent.py --id 11 --stake 8 --proposal Block_BAD --byz
"""
from __future__ import annotations
import argparse
import json
import threading
import time
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer

from security import generate_keys, sign_message
from transaction import Transaction


class Agent:
    # ------------------------------------------------------------------ #
    #  Construction                                                      #
    # ------------------------------------------------------------------ #
    def __init__(self, agent_id: int, stake: int, proposal_meta: str, is_byzantine: bool):
        self.agent_id = agent_id
        self.stake = stake
        self.proposal_metadata = proposal_meta
        self.is_byzantine = is_byzantine

        self.private_key, self.public_key = generate_keys()

        # ---------------- Producer ------------------------------------ #
        self.producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=30_000,
        )

        # ---------------- Consumer ------------------------------------ #
        self.consumer = KafkaConsumer(
            "election",
            "proposal",
            bootstrap_servers="localhost:9092",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            group_id=f"agent-{self.agent_id}",
        )

        # ---------------- State flags --------------------------------- #
        self.current_round: int | None = None
        self.leader_id: int | None = None
        self._proposed = False
        self._voted = False

        # ---------------- Threads ------------------------------------- #
        self.listener = threading.Thread(target=self._background_loop, daemon=True)
        self.listener.start()

        self.heartbeat = threading.Thread(target=self._leader_heartbeat, daemon=True)
        self.heartbeat.start()

    # ------------------------------------------------------------------ #
    #  Background Kafka loop                                             #
    # ------------------------------------------------------------------ #
    def _background_loop(self):
        print(f"🧵 Agent {self.agent_id} listener running")
        for record in self.consumer:
            topic, msg = record.topic, record.value
            if topic == "election":
                self._handle_election(msg)
            elif topic == "proposal":
                self._handle_proposal(msg)

    # ------------------------------------------------------------------ #
    #  Election and proposal handling                                    #
    # ------------------------------------------------------------------ #
    def _handle_election(self, msg: dict):
        """Called when *any* election arrives."""
        self.current_round = msg["round"]
        self.leader_id = msg["leader_id"]
        self._proposed = False
        self._voted = False

        if self.leader_id == self.agent_id:
            print(f"👑 Agent {self.agent_id} elected leader for round {self.current_round}")
            self._send_proposal()          # first attempt immediately

    def _send_proposal(self):
        if self._proposed:
            return
        tx = self._create_proposal_tx()
        proposal_dict = {
            "proposer": tx.proposer,
            "action": tx.action,
            "metadata": tx.metadata,
            "timestamp": tx.timestamp,
            "signature": tx.signature.hex(),
            "public_key": tx.public_key.decode(),
        }
        self.producer.send("proposal", proposal_dict)
        self.producer.flush()
        self._proposed = True
        print(f"🚀 Agent {self.agent_id} broadcast proposal {tx.metadata}")

    def _handle_proposal(self, msg: dict):
        """Follower (or leader itself) receives the leader’s block and votes."""
        if self._voted:
            return
        if msg["metadata"] != self.proposal_metadata:
            return  # honest policy: ignore blocks we don't support

        tx = Transaction(
            proposer=msg["proposer"],
            action=msg["action"],
            metadata=msg["metadata"],
            timestamp=msg["timestamp"],
        )
        tx.signature = bytes.fromhex(msg["signature"])
        tx.public_key = msg["public_key"].encode()
        self._publish_vote_for(tx)
        self._voted = True
        print(f"🗳  Agent {self.agent_id} voted for {tx.metadata}")

    # ------------------------------------------------------------------ #
    #  Leader heartbeat / retry                                          #
    # ------------------------------------------------------------------ #
    def _leader_heartbeat(self):
        while True:
            time.sleep(1.5)
            if (
                self.leader_id == self.agent_id
                and not self._proposed
                and self.current_round is not None
            ):
                print(f"⏰ Agent {self.agent_id} retrying proposal (round {self.current_round})")
                self._send_proposal()

    # ------------------------------------------------------------------ #
    #  Vote publishing helper                                            #
    # ------------------------------------------------------------------ #
    def _publish_vote_for(self, proposal: Transaction):
        if not proposal.verify_signature(proposal.public_key):
            print(f"⚠️  Agent {self.agent_id}: leader signature invalid")
            return

        vote_msg = f"{self.agent_id}:{proposal.metadata}"
        vote_sig = sign_message(vote_msg, self.private_key)

        payload = {
            "id": self.agent_id,
            "weight": self.stake,
            "vote_signature": vote_sig.hex(),
            "voter_pub_key": self.public_key.decode(),
            "proposal": {
                "proposer": proposal.proposer,
                "action": proposal.action,
                "metadata": proposal.metadata,
                "timestamp": proposal.timestamp,
                "signature": proposal.signature.hex(),
                "public_key": proposal.public_key.decode(),
            },
        }
        self.producer.send("votes", payload)
        self.producer.flush()

    # ------------------------------------------------------------------ #
    #  Helper: build proposal transaction                                #
    # ------------------------------------------------------------------ #
    def _create_proposal_tx(self) -> Transaction:
        tx = Transaction(
            proposer=self.agent_id,
            action="PROPOSE_BLOCK",
            metadata=self.proposal_metadata,
            timestamp=str(datetime.now(timezone.utc).isoformat()),
        )
        tx.sign_transaction(self.private_key)
        tx.public_key = self.public_key
        return tx

    # ------------------------------------------------------------------ #
    #  Shutdown                                                          #
    # ------------------------------------------------------------------ #
    def shutdown(self):
        try:
            self.producer.flush()
            self.producer.close()
            self.consumer.close()
        except Exception as exc:
            print(f"Agent {self.agent_id} close error: {exc}")


# ---------------------------------------------------------------------- #
#  CLI entry                                                             #
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True, help="Agent ID")
    ap.add_argument("--stake", type=int, required=True, help="Stake value")
    ap.add_argument("--proposal", type=str, required=True, help="Preferred block metadata")
    ap.add_argument("--byz", action="store_true", help="Set if Byzantine")
    args = ap.parse_args()

    # stagger startup a little
    time.sleep(args.id * 0.05)

    agent = Agent(args.id, args.stake, args.proposal, args.byz)

    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        agent.shutdown()
