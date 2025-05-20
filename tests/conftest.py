import string
from random import choice, randint

import pytest
from faker import Faker
from faker.providers import BaseProvider
from flask import Flask
from flask.testing import FlaskClient

from eligibility_signposting_api.app import create_app


@pytest.fixture(scope="session")
def app() -> Flask:
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> FlaskClient:
    return app.test_client()


@pytest.fixture(scope="session")
def faker() -> Faker:
    faker = Faker("en_UK")
    faker.add_provider(PersonDetailProvider)
    return faker


class PersonDetailProvider(BaseProvider):
    def nhs_number(self) -> str:
        return f"5{randint(1, 999999999):09}"

    def icb(self) -> str | None:
        if randint(0, 3):
            return f"{choice(string.ascii_uppercase)}{choice(string.ascii_uppercase)}{choice(string.digits)}"
        return None

    def gp_practice(self) -> str | None:
        if randint(0, 3):
            return f"{choice(string.ascii_uppercase)}{randint(1, 99999):05}"
        return None

    def pcn(self) -> str | None:
        if randint(0, 3):
            return f"{choice(string.ascii_uppercase)}{randint(1, 99999):05}"
        return None

    def comissioning_region(self) -> str | None:
        if randint(0, 3):
            return f"{choice(string.ascii_uppercase)}{randint(1, 99):02}"
        return None

    def msoa(self) -> str | None:
        if randint(0, 3):
            return f"{choice(string.ascii_uppercase)}{randint(1, 99999999):08}"
        return None

    def lsoa(self) -> str | None:
        if randint(0, 3):
            return f"{choice(string.ascii_uppercase)}{randint(1, 99999999):08}"
        return None
