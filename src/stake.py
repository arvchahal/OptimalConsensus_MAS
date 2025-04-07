####stake.py
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
        Select the top N agents with highest stakes as validators.
        
        Parameters:
        num_validators: Number of validators to select
        
        Returns:
        list: IDs of selected validator agents
        """
        # If fewer agents exist than requested, just return them all
        if len(self.stakes) <= num_validators:
            return list(self.stakes.keys())

        # Sort agents by stake (highest first) and select top N
        sorted_agents = sorted(self.stakes.items(), key=lambda x: x[1], reverse=True)
        top_validators = [agent_id for agent_id, stake in sorted_agents[:num_validators]]
        
        self.total_validators = len(top_validators)
        return top_validators

    def slash(self, agent_id, slash_percentage):
        """
        Reduce an agent's stake as penalty for bad behavior
        
        Parameters:
        agent_id: The ID of the agent to slash
        slash_percentage: Percentage of stake to slash (0.0-1.0)
        
        Returns:
        int: Amount slashed
        """
        if agent_id in self.stakes:
            slash_amount = int(self.stakes[agent_id] * slash_percentage)
            self.stakes[agent_id] -= slash_amount
            # Enforce minimum stake of 1
            if self.stakes[agent_id] < 1:
                self.stakes[agent_id] = 1
            return slash_amount
        return 0
