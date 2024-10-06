from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from .models import Account, Base, Currency, Flow, Operation, State, Transaction, Wallet


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    connection.close()


class TestAccount:
    def test_create_account(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        assert db_session.query(Account).count() == 1
        assert db_session.query(Account).first().name == "test"

    def test_create_account_null_name(self, db_session):
        account = Account()
        db_session.add(account)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_existing_account(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        account = Account(name="test")
        db_session.add(account)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWallet:
    def test_create_wallet(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        db_session.add(wallet)
        db_session.commit()

        assert db_session.query(Wallet).count() == 1
        assert db_session.query(Wallet).first().name == "test"
        assert db_session.query(Wallet).first().currency == Currency.USD

    def test_create_wallet_default_currency(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        wallet = Wallet(name="test", account=account)
        db_session.add(wallet)
        db_session.commit()

        assert db_session.query(Wallet).count() == 1
        assert db_session.query(Wallet).first().name == "test"
        assert db_session.query(Wallet).first().currency == Currency.EUR

    def test_create_wallet_for_non_existing_account(self, db_session):
        wallet = Wallet(name="test", account_id=1, currency=Currency.USD)
        db_session.add(wallet)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_wallet_null_name(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        wallet = Wallet(account=account, currency=Currency.USD)
        db_session.add(wallet)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_wallet_null_currency(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        wallet = Wallet(name="test", account=account)
        db_session.add(wallet)

        db_session.commit()

        assert db_session.query(Wallet).count() == 1
        assert db_session.query(Wallet).first().name == "test"
        assert db_session.query(Wallet).first().currency == Currency.EUR

    def test_create_wallet_null_account(self, db_session):
        wallet = Wallet(name="test", currency=Currency.USD)
        db_session.add(wallet)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_wallet_with_existing_name(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        db_session.add_all([account, wallet])
        db_session.commit()

        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        db_session.add(wallet)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_wallet_balance(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow = Flow(amount=100, wallet=wallet, transaction=transaction)
        db_session.add_all([account, wallet, transaction, flow])
        db_session.commit()

        assert db_session.query(Wallet).first().balance == 100
        assert db_session.query(Wallet).first().pending_balance == 100

    def test_wallet_balance_with_multiple_flows(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction1 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow1 = Flow(amount=100, wallet=wallet, transaction=transaction1)
        transaction2 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow2 = Flow(amount=200, wallet=wallet, transaction=transaction2)
        db_session.add_all([account, wallet, transaction1, flow1, transaction2, flow2])
        db_session.commit()

        assert db_session.query(Wallet).first().balance == 300
        assert db_session.query(Wallet).first().pending_balance == 300

    def test_wallet_balance_with_no_flows(self, db_session):
        account = Account(name="test")
        db_session.add(account)
        db_session.commit()

        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        db_session.add(wallet)
        db_session.commit()

        assert db_session.query(Wallet).first().balance == 0
        assert db_session.query(Wallet).first().pending_balance == 0

    def test_wallet_balance_with_negative_flows(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow1 = Flow(amount=100, wallet=wallet, transaction=transaction)
        flow2 = Flow(amount=-200, wallet=wallet, transaction=transaction)
        db_session.add_all([account, wallet, transaction, flow1, flow2])
        db_session.commit()

        assert db_session.query(Wallet).first().balance == -100
        assert db_session.query(Wallet).first().pending_balance == -100

    def test_wallet_balance_with_pending_flows(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction1 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow1 = Flow(
            amount=100, wallet=wallet, transaction=transaction1, state=State.PDG
        )
        transaction2 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow2 = Flow(
            amount=200, wallet=wallet, transaction=transaction2, state=State.PDG
        )
        db_session.add_all([account, wallet, transaction1, flow1, transaction2, flow2])
        db_session.commit()

        assert db_session.query(Wallet).first().balance == 0
        assert db_session.query(Wallet).first().pending_balance == 300

    def test_wallet_balance_with_reverted_flows(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction1 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow1 = Flow(
            amount=100, wallet=wallet, state=State.RVT, transaction=transaction1
        )
        transaction2 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow2 = Flow(
            amount=200, wallet=wallet, state=State.RVT, transaction=transaction2
        )
        db_session.add_all([account, wallet, transaction1, flow1, transaction2, flow2])
        db_session.commit()

        assert db_session.query(Wallet).first().balance == 0
        assert db_session.query(Wallet).first().pending_balance == 0

    def test_wallet_balance_with_mixed_flows(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction1 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow1 = Flow(amount=100, wallet=wallet, transaction=transaction1)
        transaction2 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow2 = Flow(amount=-200, wallet=wallet, transaction=transaction2)
        transaction3 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow3 = Flow(
            amount=300, wallet=wallet, transaction=transaction3, state=State.PDG
        )
        transaction4 = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        flow4 = Flow(
            amount=400, wallet=wallet, transaction=transaction4, state=State.RVT
        )
        db_session.add_all(
            [
                account,
                wallet,
                transaction1,
                flow1,
                transaction2,
                flow2,
                transaction3,
                flow3,
                transaction4,
                flow4,
            ]
        )
        db_session.commit()

        assert db_session.query(Wallet).first().balance == -100
        assert db_session.query(Wallet).first().pending_balance == 200


class TestTransaction:
    def test_create_transaction(self, db_session):
        now = datetime.now()
        transaction = Transaction(type=Operation.PAY, date=now, description="test")
        db_session.add(transaction)
        db_session.commit()

        assert db_session.query(Transaction).count() == 1
        assert db_session.query(Transaction).first().type == Operation.PAY
        assert db_session.query(Transaction).first().date == now
        assert db_session.query(Transaction).first().description == "test"

    def test_create_transaction_null_description(self, db_session):
        now = datetime.now()
        transaction = Transaction(type=Operation.PAY, date=now, description=None)
        db_session.add(transaction)
        db_session.commit()

        assert db_session.query(Transaction).count() == 1
        assert db_session.query(Transaction).first().type == Operation.PAY
        assert db_session.query(Transaction).first().date == now
        assert db_session.query(Transaction).first().description is None

    def test_create_transaction_null_type(self, db_session):
        now = datetime.now()
        transaction = Transaction(date=now, type=None)
        db_session.add(transaction)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_transaction_null_date(self, db_session):
        transaction = Transaction(type=Operation.PAY, date=None)
        db_session.add(transaction)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestFlow:
    def test_create_flow(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        db_session.add_all([account, wallet, transaction])
        db_session.commit()

        flow = Flow(amount=100, wallet=wallet, state=State.CPL, transaction=transaction)
        db_session.add(flow)
        db_session.commit()

        assert db_session.query(Flow).count() == 1
        assert db_session.query(Flow).first().amount == 100
        assert db_session.query(Flow).first().wallet_id == wallet.id
        assert db_session.query(Flow).first().state == State.CPL

    def test_create_flow_reverted(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        db_session.add_all([account, wallet, transaction])
        db_session.commit()

        flow = Flow(amount=100, wallet=wallet, state=State.RVT, transaction=transaction)
        db_session.add(flow)
        db_session.commit()

        assert db_session.query(Flow).count() == 1
        assert db_session.query(Flow).first().amount == 100
        assert db_session.query(Flow).first().wallet_id == wallet.id
        assert db_session.query(Flow).first().state == State.RVT

    def test_create_flow_pending(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        db_session.add_all([account, wallet, transaction])
        db_session.commit()

        flow = Flow(amount=100, wallet=wallet, state=State.PDG, transaction=transaction)
        db_session.add(flow)
        db_session.commit()

        assert db_session.query(Flow).count() == 1
        assert db_session.query(Flow).first().amount == 100
        assert db_session.query(Flow).first().wallet_id == wallet.id
        assert db_session.query(Flow).first().state == State.PDG

    def test_create_flow_default_state(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        db_session.add_all([account, wallet, transaction])
        db_session.commit()

        flow = Flow(amount=100, wallet=wallet, transaction=transaction)
        db_session.add(flow)
        db_session.commit()

        assert db_session.query(Flow).count() == 1
        assert db_session.query(Flow).first().amount == 100
        assert db_session.query(Flow).first().wallet_id == wallet.id
        assert db_session.query(Flow).first().state == State.CPL

    def test_create_flow_for_non_existing_wallet(self, db_session):
        flow = Flow(amount=100, wallet_id=1)
        db_session.add(flow)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_flow_for_non_existing_transaction(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        db_session.add_all([account, wallet])
        db_session.commit()

        flow = Flow(amount=100, wallet=wallet, transaction_id=1)
        db_session.add(flow)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_flow_null_wallet(self, db_session):
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )

        flow = Flow(amount=100, transaction=transaction, wallet=None)
        db_session.add(flow)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_flow_null_transaction(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        db_session.add_all([account, wallet])
        db_session.commit()

        flow = Flow(amount=100, wallet=wallet, transaction=None)
        db_session.add(flow)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_flow_null_amount(self, db_session):
        account = Account(name="test")
        wallet = Wallet(name="test", account=account, currency=Currency.USD)
        transaction = Transaction(
            type=Operation.PAY, date=datetime.now(), description="test"
        )
        db_session.add_all([account, wallet, transaction])
        db_session.commit()

        flow = Flow(wallet=wallet, transaction=transaction, amount=None)
        db_session.add(flow)

        with pytest.raises(IntegrityError):
            db_session.commit()
