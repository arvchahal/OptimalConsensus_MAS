####voteverifier.py

import time
class VoteVerifier:
    def __init__(self):
        self.bad_votes = {}  # Track bad votes by agent_id
    
    def verify_vote(self, vote, agent_id, public_key, expected_proposal=None):
        """
        Verify if a vote is valid.
        Returns True if valid, False if invalid.
        """
        # 1. Verify signature is valid
        if not vote.verify_signature(public_key):
            self._record_bad_vote(agent_id, "invalid_signature")
            return False
            
        # 2. Check vote is for current round (prevents replay attacks)
        current_time = time.time()
        if abs(vote.timestamp - current_time) > 300:  # 5 minute tolerance
            self._record_bad_vote(agent_id, "stale_vote")
            return False
            
        # 3. If we know what proposal is being voted on, verify vote is for that
        if expected_proposal and vote.proposal_id != expected_proposal.id:
            self._record_bad_vote(agent_id, "wrong_proposal")
            return False
            
        return True
    
    def _record_bad_vote(self, agent_id, reason):
        if agent_id not in self.bad_votes:
            self.bad_votes[agent_id] = []
        self.bad_votes[agent_id].append(reason)
