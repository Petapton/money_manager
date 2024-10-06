import decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from . import app, get_db
from .database import Base

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_connection():
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()

    yield connection

    connection.close()


@pytest.fixture(scope="function")
def client(db_connection):
    transaction = db_connection.begin()
    session = SessionLocal(bind=db_connection)

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

    session.close()
    transaction.rollback()


def create_test_account(_client):
    return _client.post("/accounts/", json={"name": "test"})


def create_test_wallet(_client):
    return _client.post(
        "/wallets/", json={"name": "test", "currency": "USD", "account_id": 1}
    )


def create_test_flow(_client):
    return _client.post(
        "/flows/",
        json={"amount": "100.00", "wallet_id": 1, "transaction_id": 1, "state": "CPL"},
    )


def create_test_transaction(_client):
    return _client.post(
        "/transactions/",
        json={
            "type": "INC",
            "description": "test",
            "date": "2021-01-01T00:00:00",
        },
    )


class TestAccount:
    def test_create_account(self, client):
        response = create_test_account(client)
        assert response.status_code == 200
        assert response.json()["name"] == "test"

    def test_create_account_duplicate(self, client):
        response = create_test_account(client)
        assert response.status_code == 200

        response = create_test_account(client)
        assert response.status_code == 409
        assert response.json() == {"detail": "Account name already exists"}

    def test_read_accounts(self, client):
        response = client.get("/accounts/")
        assert response.status_code == 200
        assert response.json() == []

        create_test_account(client)
        response = client.get("/accounts/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "test"


class TestWallet:
    def test_create_wallet(self, client):
        create_test_account(client)
        response = create_test_wallet(client)
        assert response.status_code == 200
        assert response.json()["name"] == "test"
        assert response.json()["currency"] == "USD"
        assert decimal.Decimal(response.json()["balance"]) == 0

    def test_create_wallet_duplicate(self, client):
        create_test_account(client)
        response = create_test_wallet(client)
        assert response.status_code == 200

        response = create_test_wallet(client)
        assert response.status_code == 409
        assert response.json() == {
            "detail": "Wallet name already exists for this account"
        }

    def test_create_wallet_no_currency(self, client):
        create_test_account(client)
        response = client.post("/wallets/", json={"name": "test", "account_id": 1})
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "currency"]

    def test_create_wallet_invalid_currency(self, client):
        create_test_account(client)
        response = client.post(
            "/wallets/", json={"name": "test", "currency": "INVALID", "account_id": 1}
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "currency"]

    def test_create_wallet_no_account(self, client):
        create_test_account(client)
        response = client.post(
            "/wallets/",
            json={"name": "test", "currency": "USD"},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "account_id"]

    def test_create_wallet_invalid_account(self, client):
        create_test_account(client)
        response = client.post(
            "/wallets/",
            json={"name": "test", "currency": "USD", "account_id": 2},
        )
        assert response.status_code == 404

    def test_read_wallets(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = client.get("/wallets/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "test"
        assert response.json()[0]["currency"] == "USD"
        assert decimal.Decimal(response.json()[0]["balance"]) == 0


class TestTransaction:
    def test_create_transaction(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = create_test_transaction(client)
        print(response.json())
        assert response.status_code == 200
        assert response.json()["type"] == "INC"
        assert response.json()["description"] == "test"
        assert response.json()["date"] == "2021-01-01T00:00:00"

    def test_create_transaction_no_type(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = client.post(
            "/transactions/",
            json={
                "description": "test",
                "date": "2021-01-01T00:00:00",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "type"]

    def test_create_transaction_invalid_type(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = client.post(
            "/transactions/",
            json={
                "type": "INVALID",
                "description": "test",
                "date": "2021-01-01T00:00:00",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "type"]

    def test_create_transaction_no_description(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = client.post(
            "/transactions/",
            json={
                "type": "INC",
                "date": "2021-01-01T00:00:00",
            },
        )
        assert response.status_code == 200
        assert response.json()["description"] is None

    def test_create_transaction_no_date(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = client.post(
            "/transactions/",
            json={
                "type": "INC",
                "description": "test",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "date"]

    def test_create_transaction_invalid_date(self, client):
        create_test_account(client)
        create_test_wallet(client)
        response = client.post(
            "/transactions/",
            json={
                "type": "INC",
                "description": "test",
                "date": "INVALID",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "date"]

    def test_read_transactions(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.get("/transactions/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["type"] == "INC"
        assert response.json()[0]["description"] == "test"
        assert response.json()[0]["date"] == "2021-01-01T00:00:00"


class TestFlow:
    def test_create_flow(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = create_test_flow(client)
        assert response.status_code == 200
        assert decimal.Decimal(response.json()["amount"]) == 100.00

    def test_create_flow_no_amount(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={"wallet_id": 1, "transaction_id": 1, "state": "CPL"},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "amount"]

    def test_create_flow_invalid_amount(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={
                "amount": "INVALID",
                "wallet_id": 1,
                "transaction_id": 1,
                "state": "CPL",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "amount"]

    def test_create_flow_no_wallet(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={"amount": "100.00", "transaction_id": 1, "state": "CPL"},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "wallet_id"]

    def test_create_flow_invalid_wallet(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={
                "amount": "100.00",
                "wallet_id": 2,
                "transaction_id": 1,
                "state": "CPL",
            },
        )
        assert response.status_code == 404

    def test_create_flow_no_transaction(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={"amount": "100.00", "wallet_id": 1, "state": "CPL"},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "transaction_id"]

    def test_create_flow_invalid_transaction(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={
                "amount": "100.00",
                "wallet_id": 1,
                "transaction_id": 2,
                "state": "CPL",
            },
        )
        assert response.status_code == 404

    def test_create_flow_no_state(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={"amount": "100.00", "wallet_id": 1, "transaction_id": 1},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "state"]

    def test_create_flow_invalid_state(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        response = client.post(
            "/flows/",
            json={
                "amount": "100.00",
                "wallet_id": 1,
                "transaction_id": 1,
                "state": "INVALID",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "state"]

    def test_read_flows(self, client):
        create_test_account(client)
        create_test_wallet(client)
        create_test_transaction(client)
        create_test_flow(client)
        response = client.get("/flows/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert decimal.Decimal(response.json()[0]["amount"]) == 100.00
        assert response.json()[0]["wallet_id"] == 1
        assert response.json()[0]["transaction_id"] == 1
