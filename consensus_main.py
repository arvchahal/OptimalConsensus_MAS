# consensus_main.py
import sys
from stake import Stake
from consensus import Consensus

if __name__ == "__main__":
    # Expect two args + a list of agent stakes via stdin or a file
    # e.g. usage: python consensus_main.py 0.67 100 "agent_stakes.txt"
    if len(sys.argv) < 3:
        print("Usage: python consensus_main.py <threshold> <total_stake>")
        sys.exit(1)

    threshold = float(sys.argv[1])
    total_stake = int(sys.argv[2])

    # Initialize Stake system
    st = Stake()

    # We’ll read lines from a local file (or STDIN) to fill st
    # For example: each line: "agent_id stake"
    # But let's assume you wrote them to "agent_stakes.txt" in the shell script
    # If we want a simpler approach, see the updated shell script below.

    with open("agent_stakes.txt", "r") as f:
        for line in f:
            agent_id_str, stake_str = line.strip().split()
            agent_id = int(agent_id_str)
            stake_amt = int(stake_str)
            st.stake(agent_id, stake_amt)

    # Create consensus with stake system
    consensus = Consensus(threshold, total_stake, stake_system=st)
    consensus.listen()
