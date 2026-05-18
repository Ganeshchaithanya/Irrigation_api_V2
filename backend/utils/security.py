import secrets
import string

def generate_pairing_code(length=8):
    """
    Generates a cryptographically strong random string for device pairing.
    Avoids predictable patterns.
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
