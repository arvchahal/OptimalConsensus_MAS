import random
import time
from stake import Stake
from consensus import Consensus
from agent import Agent
from vote import Vote

def test_slashing():
    print("===== Testing Slashing Mechanism =====")
    
    # Create agents
    num_agents = 5
    agents = [Agent(i) for i in range(1, num_agents + 1)]
    
    # Initialize stake system
    stake_system = Stake()
    for agent in agents:
        stake_amount = 50  # Fixed initial stake for easier tracking
        stake_system.stake(agent.agent_id, stake_amount)
        print(f"Agent {agent.agent_id} staked {stake_amount}")
    
    # Select validators (all agents for this test)
    validators_ids = list(range(1, num_agents + 1))
    print(f"\nValidators: {validators_ids}")
    
    # Create a leader and proposal
    leader = agents[0]
    leader.is_leader = True
    proposal = leader.propose()
    print(f"\nProposal: {proposal}")
    
    # Calculate total stake
    total_validator_stake = sum([stake_system.stakes[vid] for vid in validators_ids])
    print(f"Total validator stake: {total_validator_stake}")
    
    # Initialize consensus system
    consensus = Consensus(0.67, total_validator_stake, stake_system)
    consensus.set_current_proposal(proposal)
    
    # Test scenario 1: All valid votes
    print("\n--- Scenario 1: All valid votes ---")
    consensus.votes = {}  # Reset votes
    
    for agent in agents:
        weight = stake_system.stakes[agent.agent_id]
        vote = agent.create_valid_vote(proposal)
        success = consensus.register_vote(
            proposal, agent.agent_id, weight,
            vote.signature, agent.public_key
        )
        print(f"Agent {agent.agent_id} voted {'successfully' if success else 'unsuccessfully'} with stake {weight}")
    
    # Check consensus
    result = consensus.aggregate_votes()
    print(f"Consensus result: {'Reached' if result else 'Not reached'}")
    
    # Test scenario 2: Mix of valid and invalid votes
    print("\n--- Scenario 2: Mix of valid and invalid votes ---")
    consensus.votes = {}  # Reset votes
    
    # Reset stakes for this scenario
    for agent in agents:
        stake_system.stakes[agent.agent_id] = 50
    
    for agent in agents:
        weight = stake_system.stakes[agent.agent_id]
        
        # Make agents 2 and 4 submit bad votes
        if agent.agent_id in [2, 4]:
            vote = agent.create_bad_vote(proposal)
            print(f"Agent {agent.agent_id} is submitting a bad vote...")
        else:
            vote = agent.create_valid_vote(proposal)
            
        success = consensus.register_vote(
            proposal, agent.agent_id, weight,
            vote.signature, agent.public_key
        )
        
        # Get updated weight after potential slashing
        updated_weight = stake_system.stakes[agent.agent_id]
        print(f"Agent {agent.agent_id} voted {'successfully' if success else 'unsuccessfully'} " + 
              f"with stake now at {updated_weight}")
    
    # Check consensus
    result = consensus.aggregate_votes()
    print(f"Consensus result: {'Reached' if result else 'Not reached'}")
    
    # Show final stakes
    print("\nFinal stakes after slashing:")
    for agent_id, stake in stake_system.stakes.items():
        print(f"Agent {agent_id}: {stake}")

if __name__ == "__main__":
    test_slashing() 