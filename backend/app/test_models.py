import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .models import Account, Base, Currency, Flow, State, Wallet


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


def test_create_account(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    assert db_session.query(Account).count() == 1
    assert db_session.query(Account).first().name == "test"


def test_create_wallet(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    assert db_session.query(Wallet).count() == 1
    assert db_session.query(Wallet).first().name == "test"
    assert db_session.query(Wallet).first().currency == Currency.USD


def test_create_flow(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id, state=State.CPL)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Flow).count() == 1
    assert db_session.query(Flow).first().amount == 100
    assert db_session.query(Flow).first().wallet_id == wallet.id
    assert db_session.query(Flow).first().state == State.CPL


def test_create_flow_reverted(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id, state=State.RVT)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Flow).count() == 1
    assert db_session.query(Flow).first().amount == 100
    assert db_session.query(Flow).first().wallet_id == wallet.id
    assert db_session.query(Flow).first().state == State.RVT


def test_create_flow_pending(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id, state=State.PDG)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Flow).count() == 1
    assert db_session.query(Flow).first().amount == 100
    assert db_session.query(Flow).first().wallet_id == wallet.id
    assert db_session.query(Flow).first().state == State.PDG


def test_create_flow_default_state(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Flow).count() == 1
    assert db_session.query(Flow).first().amount == 100
    assert db_session.query(Flow).first().wallet_id == wallet.id
    assert db_session.query(Flow).first().state is State.CPL


def test_wallet_balance(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == 100
    assert db_session.query(Wallet).first().pending_balance == 100


def test_wallet_balance_with_multiple_flows(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow1 = Flow(amount=100, wallet_id=wallet.id)
    db_session.add(flow1)
    db_session.commit()

    flow2 = Flow(amount=200, wallet_id=wallet.id)
    db_session.add(flow2)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == 300
    assert db_session.query(Wallet).first().pending_balance == 300


def test_wallet_balance_with_no_flows(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == 0
    assert db_session.query(Wallet).first().pending_balance == 0


def test_wallet_balance_with_negative_flows(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=-100, wallet_id=wallet.id)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == -100
    assert db_session.query(Wallet).first().pending_balance == -100


def test_wallet_balance_with_pending_flows(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow1 = Flow(amount=100, wallet_id=wallet.id, state=State.PDG)
    db_session.add(flow1)
    db_session.commit()

    flow2 = Flow(amount=200, wallet_id=wallet.id, state=State.PDG)
    db_session.add(flow2)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == 0
    assert db_session.query(Wallet).first().pending_balance == 300


def test_wallet_balance_with_reverted_flows(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow1 = Flow(amount=100, wallet_id=wallet.id, state=State.RVT)
    db_session.add(flow1)
    db_session.commit()

    flow2 = Flow(amount=200, wallet_id=wallet.id, state=State.RVT)
    db_session.add(flow2)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == 0
    assert db_session.query(Wallet).first().pending_balance == 0


def test_wallet_balance_with_mixed_flows(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow1 = Flow(amount=100, wallet_id=wallet.id, state=State.CPL)
    db_session.add(flow1)
    db_session.commit()

    flow2 = Flow(amount=200, wallet_id=wallet.id, state=State.PDG)
    db_session.add(flow2)
    db_session.commit()

    flow3 = Flow(amount=300, wallet_id=wallet.id, state=State.RVT)
    db_session.add(flow3)
    db_session.commit()

    flow4 = Flow(amount=-400, wallet_id=wallet.id, state=State.CPL)
    db_session.add(flow4)
    db_session.commit()

    flow5 = Flow(amount=-500, wallet_id=wallet.id, state=State.PDG)
    db_session.add(flow5)
    db_session.commit()

    flow6 = Flow(amount=-600, wallet_id=wallet.id, state=State.RVT)
    db_session.add(flow6)
    db_session.commit()

    assert db_session.query(Wallet).first().balance == -300
    assert db_session.query(Wallet).first().pending_balance == -600


def test_create_transaction(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id)
    db_session.add(flow)
    db_session.commit()

    assert db_session.query(Flow).count() == 1
    assert db_session.query(Flow).first().amount == 100
    assert db_session.query(Flow).first().wallet_id == wallet.id
    assert db_session.query(Flow).first().transaction_id is None
    assert db_session.query(Flow).first().wallet.balance == 100


def test_create_existing_account(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    account = Account(name="test")
    db_session.add(account)

    with pytest.raises(Exception):
        db_session.commit()


def test_create_existing_wallet(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)

    with pytest.raises(Exception):
        db_session.commit()


def test_create_flow_for_non_existing_wallet(db_session):
    flow = Flow(amount=100, wallet_id=1)
    db_session.add(flow)

    with pytest.raises(Exception):
        db_session.commit()


def test_create_flow_for_non_existing_transaction(db_session):
    account = Account(name="test")
    db_session.add(account)
    db_session.commit()

    wallet = Wallet(name="test", account_id=account.id, currency=Currency.USD)
    db_session.add(wallet)
    db_session.commit()

    flow = Flow(amount=100, wallet_id=wallet.id, transaction_id=1)
    db_session.add(flow)

    with pytest.raises(Exception):
        db_session.commit()
