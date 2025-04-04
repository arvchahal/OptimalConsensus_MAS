#########################
# security.py (already fine)
#########################
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

def generate_keys(key_size=2048):
    key = RSA.generate(key_size)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    return private_key, public_key

def sign_message(message, private_key_bytes):
    key = RSA.import_key(private_key_bytes)
    h = SHA256.new(message.encode())
    return pkcs1_15.new(key).sign(h)

def verify_signature(message, signature, public_key_bytes):
    key = RSA.import_key(public_key_bytes)
    h = SHA256.new(message.encode())
    try:
        pkcs1_15.new(key).verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False
