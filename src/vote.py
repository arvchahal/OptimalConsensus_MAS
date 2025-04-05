from transaction import Transaction
import time

class Vote(Transaction):
    def __init__(self, voter_id, proposal, signature=None):
        # Use the Transaction class for signature management
        super().__init__(
            proposer=voter_id,
            action="vote",
            metadata={"proposal_id": proposal},
            timestamp=time.time()
        )
        if signature:
            self.signature = signature
            
    @property
    def proposal_id(self):
        return self.metadata.get("proposal_id")
