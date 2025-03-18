import random

class Stake:
    def __init__(self):
        self.stakes = {}
        self.total_validators = 0

    def stake(self, agent_id, resource_amt):
        if agent_id in self.stakes:
            self.stakes[agent_id] += resource_amt
        else:
            self.stakes[agent_id] = resource_amt

    def withdraw(self, agent_id, amount):
        if agent_id in self.stakes and amount <= self.stakes[agent_id]:
            self.stakes[agent_id] -= amount
            if self.stakes[agent_id] == 0:
                del self.stakes[agent_id]
        else:
            raise ValueError("Can't withdraw")

    def select_validators(self, num_validators):
        """
        Select a subset of agents as validators, weighted by stake.
        """
        # If fewer agents exist than requested, just return them all
        if len(self.stakes) <= num_validators:
            return list(self.stakes.keys())

        agent_ids = list(self.stakes.keys())
        weights = [self.stakes[a] for a in agent_ids]
        chosen = random.choices(agent_ids, weights=weights, k=num_validators)

        # Avoid duplicates if random.choices picks the same agent multiple times
        self.total_validators = len(set(chosen))
        return list(set(chosen))
