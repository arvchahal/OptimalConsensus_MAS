import argparse
import random
import time
import matplotlib.pyplot as plt
from stake import Stake
from consensus import Consensus
from agent import Agent

def run_proposal(agents, validators_ids, stake_system, threshold):
    # Determine a leader among validators (for simplicity, pick the first validator)
    leader_id = validators_ids[0]
    leader = next(agent for agent in agents if agent.agent_id == leader_id)
    leader.is_leader = True

    # Leader proposes a block.
    proposal = leader.propose()

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
            if consensus_instance.is_threshold_reached():
                print("Early exit: threshold reached, stopping further votes.")
                break

    # Aggregate votes and determine if consensus is reached.
    accepted_block = consensus_instance.aggregate_votes()
    return accepted_block

def main(num_agents, num_validators, threshold, iterations):
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

    # List to store timing results.
    timings = []

    for i in range(iterations):
        start_time = time.time()
        accepted_block = run_proposal(agents, validators_ids, stake_system, threshold)
        end_time = time.time()
        duration = end_time - start_time
        timings.append(duration)
        
        if accepted_block:
            print(f"\nProposal {i+1}: Consensus reached in {duration:.4f} seconds")
        else:
            print(f"\nProposal {i+1}: Consensus not reached (took {duration:.4f} seconds)")

    # Plot the timing results.
    plt.figure(figsize=(10, 6))
    plt.plot(range(1, iterations + 1), timings, marker='o')
    plt.xlabel("Proposal Number")
    plt.ylabel("Time Taken (seconds)")
    plt.title("Consensus Timing for Multiple Proposals")
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run multiple proposals in the blockchain consensus simulation.")
    parser.add_argument("--agents", type=int, default=5, help="Number of agents in the simulation.")
    parser.add_argument("--validators", type=int, default=3, help="Number of validators to select.")
    parser.add_argument("--threshold", type=float, default=0.67, help="Consensus threshold as a decimal (e.g., 0.67 for 67%).")
    parser.add_argument("--iterations", type=int, default=10, help="Number of proposals to run for timing analysis.")
    args = parser.parse_args()

    main(args.agents, args.validators, args.threshold, args.iterations)
