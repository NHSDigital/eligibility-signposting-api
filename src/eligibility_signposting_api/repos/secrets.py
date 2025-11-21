from wireup import service

@service(qualifier="nhs_hmac_key")
def nhs_hmac_key_factory() -> bytes:
    return b"abc123" # salt
