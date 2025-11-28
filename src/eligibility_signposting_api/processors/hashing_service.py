import hashlib
import hmac
from typing import Annotated, NewType

from wireup import service, Inject

from eligibility_signposting_api.repos.secret_repo import SecretRepo

HashSecretName = NewType("HashSecretName", str)


def _hash(nhs_number: str, secret_value: str) -> str:
    if not secret_value: return None

    nhs_str = str(nhs_number)

    return hmac.new(
        secret_value.encode("utf-8"),
        nhs_str.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


@service
class HashingService:
    def __init__(
        self,
        secret_repo: Annotated[SecretRepo, Inject()],
        hash_secret_name: Annotated[HashSecretName, Inject(param="hashing_secret_name")],
    ) -> None:
        super().__init__()
        self.secret_repo = secret_repo
        self.hash_secret_name = hash_secret_name

    def hash_with_current_secret(self, nhs_number: str) -> str:
        secret_value = self.secret_repo.get_secret_current(self.hash_secret_name)["AWSCURRENT"]
        return _hash(nhs_number, secret_value)

    def hash_with_previous_secret(self, nhs_number: str) -> str:
        secret_value = self.secret_repo.get_secret_previous(self.hash_secret_name)["AWSPREVIOUS"]
        return _hash(nhs_number, secret_value)
