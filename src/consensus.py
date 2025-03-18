class Consensus:
    """Implements a probabilistic PoS voting consensus"""
    def __init__(self, threshold, total_weight):
        self.threshold = threshold  # e.g., 0.67 for 67% threshold
        self.total = total_weight   # total vote weight (sum of stakes for validators)
        self.votes = {}  # dictionary mapping a candidate proposal to its weighted vote count

    def register_vote(self, candidate, weight=1):
        if candidate in self.votes:
            self.votes[candidate] += weight
        else:
            self.votes[candidate] = weight

    def aggregate_votes(self):
        # Check if any candidate's weighted vote ratio meets/exceeds the threshold.
        for candidate, vote_count in self.votes.items():
            if vote_count / self.total >= self.threshold:
                return candidate
        return None
