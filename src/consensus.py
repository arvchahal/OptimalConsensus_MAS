from vote import Vote

class Consensus:
    """Implements a probabilistic PoS voting consensus"""
    def __init__(self, threshold, total_weight, stake_system):
        self.threshold = threshold  # e.g., 0.67 for 67% threshold
        self.total = total_weight   # total vote weight (sum of stakes for validators)
        self.votes = {}  # dictionary mapping a candidate proposal to its weighted vote count
        self.stake_system = stake_system  # Reference to stake system for slashing
        self.current_proposal = None  # Current proposal being voted on
        self.bad_votes = {}  # Tracking bad votes by agent

    def set_current_proposal(self, proposal):
        """Set the current proposal being voted on"""
        self.current_proposal = proposal

    def register_vote(self, candidate, voter_id, weight=1, signature=None, public_key=None):
        """
        Register a vote with verification and slashing if vote is invalid
        
        Parameters:
        candidate: The proposal being voted on
        voter_id: ID of the voter
        weight: Weight of the vote (typically stake amount)
        signature: Signature of the vote for verification
        public_key: Public key of the voter for signature verification
        
        Returns:
        bool: Whether the vote was successfully registered
        """
        # If we have signature and public key, verify the vote
        if signature and public_key:
            # Create a vote object to verify
            vote = Vote(voter_id, candidate, signature)
            
            # Verify the vote
            if not self._verify_vote(vote, voter_id, public_key):
                # Apply slashing for bad vote
                slash_amount = self.stake_system.slash(voter_id, 0.05)  # 5% penalty
                print(f"Agent {voter_id} submitted invalid vote: slashed {slash_amount} stake")
                
                # Track the bad vote
                if voter_id not in self.bad_votes:
                    self.bad_votes[voter_id] = 0
                self.bad_votes[voter_id] += 1
                
                return False
                
        # Register the valid vote with weight
        if candidate in self.votes:
            self.votes[candidate] += weight
        else:
            self.votes[candidate] = weight
        return True

    def _verify_vote(self, vote, voter_id, public_key):
        """
        Verify if a vote is valid.
        Returns True if valid, False if invalid.
        """
        print(f"DEBUG: Verifying vote from Agent {voter_id}")
        
        # 1. Verify the signature matches
        sig_valid = vote.verify_signature(public_key)
        if not sig_valid:
            print(f"DEBUG: Signature verification failed for Agent {voter_id}")
            return False
            
        # 2. Check if voting for the current proposal
        if self.current_proposal and vote.proposal_id != self.current_proposal:
            print(f"DEBUG: Agent {voter_id} voted for wrong proposal. Expected: {self.current_proposal}, Got: {vote.proposal_id}")
            return False
            
        print(f"DEBUG: Vote from Agent {voter_id} is valid")
        return True

    def aggregate_votes(self):
        # Check if any candidate's weighted vote ratio meets/exceeds the threshold.
        for candidate, vote_count in self.votes.items():
            if vote_count / self.total >= self.threshold:
                return candidate
        return None
