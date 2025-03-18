from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

class Transaction:
    def __init__(self, proposer, action, metadata, timestamp):
        self.proposer = proposer
        self.action = action
        self.metadata = metadata
        self.timestamp = timestamp
        self.signature = None

    def sign_transaction(self, private_key_str):
        key = RSA.import_key(private_key_str)
        message = (str(self.proposer) + str(self.action) +
                   str(self.metadata) + str(self.timestamp)).encode()
        h = SHA256.new(message)
        self.signature = pkcs1_15.new(key).sign(h)

    def verify_signature(self, public_key_str):
        key = RSA.import_key(public_key_str)
        message = (str(self.proposer) + str(self.action) +
                   str(self.metadata) + str(self.timestamp)).encode()
        h = SHA256.new(message)
        try:
            pkcs1_15.new(key).verify(h, self.signature)
            return True
        except (ValueError, TypeError):
            return False
