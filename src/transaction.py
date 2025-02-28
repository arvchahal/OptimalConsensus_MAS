"""
This defines the transaction structure a transaction in general proof of stake terms
However, this could also extend work for edge AI and swarm robotics as a decision
"""
# import 
class Transaction:
    def __init__(self, proposer, action, metadata, timestamp, signature=None):
        """
        - proposer: The agent proposing an action (who initiates consensus).
        - action: The action being validated (e.g., move, allocate resources).
        - metadata: Additional info (e.g., location, task details).
        - timestamp: When it was created.
        - signature: Optional cryptographic validation.
        """
        self.proposer = proposer
        self.action = action
        self.metadata = metadata  # Could be task parameters, location, etc.
        self.timestamp = timestamp
        self.signature = signature

    def validate(self):
        """
        Validate transaction integrity.
        """
        if not self.proposer or not self.action:
            return False
        return True #can be extended with crptography

    def sign_transaction(self, private_key):
        """
        Signs the transaction (if needed for security).
        """
        self.signature = hash(str(self.proposer) + str(self.action) + str(self.metadata) + str(self.timestamp) + str(private_key))
