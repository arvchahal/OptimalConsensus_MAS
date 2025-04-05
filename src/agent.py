class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.decisions = []  # placeholder for internal decisions
        self.is_leader = False
        # Generate keys for the agent
        from security import generate_keys
        self.private_key, self.public_key = generate_keys()

    def propose(self):
        # For simplicity, generate a proposal (a block) as a string with a random number.
        import random
        proposal = f"Block proposed by Agent {self.agent_id}: {random.randint(1,100)}"
        return proposal
        
    def create_valid_vote(self, proposal):
        """Create a valid vote for the given proposal"""
        from vote import Vote
        vote = Vote(self.agent_id, proposal)
        vote.sign_transaction(self.private_key)
        return vote
        
    def create_bad_vote(self, proposal):
        """Create an invalid vote with a bad signature"""
        from vote import Vote
        import random
        
        # We can create different types of bad votes
        bad_type = random.choice(["wrong_signature", "wrong_proposal", "stale_timestamp"])
        
        if bad_type == "wrong_signature":
            # Create a vote but sign it with wrong data
            vote = Vote(self.agent_id, proposal)
            # Corrupt the vote data before signing
            vote.metadata["corrupted"] = "yes"
            vote.sign_transaction(self.private_key)
            # Remove the corruption so verification will fail
            vote.metadata.pop("corrupted")
            return vote
            
        elif bad_type == "wrong_proposal":
            # Vote for a different proposal than expected
            fake_proposal = f"Fake proposal: {random.randint(1000, 9999)}"
            vote = Vote(self.agent_id, fake_proposal)
            vote.sign_transaction(self.private_key)
            return vote
            
        elif bad_type == "stale_timestamp":
            # Create a vote with an old timestamp
            import time
            vote = Vote(self.agent_id, proposal)
            # Set timestamp to 10 minutes ago
            vote.timestamp = time.time() - 600
            vote.sign_transaction(self.private_key)
            return vote
