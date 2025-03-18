class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.decisions = []  # placeholder for internal decisions
        self.is_leader = False

    def propose(self):
        # For simplicity, generate a proposal (a block) as a string with a random number.
        import random
        proposal = f"Block proposed by Agent {self.agent_id}: {random.randint(1,100)}"
        return proposal
