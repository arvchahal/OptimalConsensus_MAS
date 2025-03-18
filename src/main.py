import argparse
import random
from stake import Stake
from consensus import Consensus
from agent import Agent

def main(num_agents, num_validators, threshold):
    # Create agents with unique IDs.
    agents = [Agent(i) for i in range(1, num_agents + 1)]

    # Initialize the stake system and assign random stakes to agents.
    stake_system = Stake()
    for agent in agents:
        stake_amount = random.randint(10, 100)
        stake_system.stake(agent.agent_id, stake_amount)
        print(f"Agent {agent.agent_id} staked {stake_amount}")

    # Select validators based on stakes.
    validators_ids = stake_system.select_validators(num_validators)
    print("\nSelected Validators:", validators_ids)

    # Determine a leader among validators (for simplicity, pick the first validator)
    leader_id = validators_ids[0]
    leader = next(agent for agent in agents if agent.agent_id == leader_id)
    leader.is_leader = True

    # Leader proposes a block.
    proposal = leader.propose()
    print("\nLeader's Proposal:")
    print(proposal)

    # Calculate total validator stake (to be used as the total vote weight)
    total_validator_stake = sum([stake_system.stakes[vid] for vid in validators_ids])
    
    # Initialize Consensus with a threshold (e.g., 67% or 0.67)
    consensus_instance = Consensus(threshold, total_validator_stake)

    # Validators vote for the leader's proposal.
    print("\nValidators Voting:")
    for agent in agents:
        if agent.agent_id in validators_ids:
            weight = stake_system.stakes[agent.agent_id]
            consensus_instance.register_vote(proposal, weight)
            print(f"Agent {agent.agent_id} (stake {weight}) voted for the proposal.")

    # Aggregate votes and determine if consensus is reached.
    accepted_block = consensus_instance.aggregate_votes()
    if accepted_block:
        print("\nConsensus reached on block:")
        print(accepted_block)
    else:
        print("\nConsensus not reached.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the blockchain consensus simulation.")
    parser.add_argument("--agents", type=int, default=5, help="Number of agents in the simulation.")
    parser.add_argument("--validators", type=int, default=3, help="Number of validators to select.")
    parser.add_argument("--threshold", type=float, default=0.67, help="Consensus threshold as a decimal (e.g., 0.67 for 67%).")
    args = parser.parse_args()

    main(args.agents, args.validators, args.threshold)
