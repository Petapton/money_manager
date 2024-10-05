from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def create_account(db: Session, account: schemas.AccountCreate):
    db_account = models.Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def get_accounts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Account).offset(skip).limit(limit).all()


def create_wallet(db: Session, wallet: schemas.WalletCreate):
    db_wallet = models.Wallet(**wallet.model_dump())
    db.add(db_wallet)
    db.commit()
    db.refresh(db_wallet)
    return db_wallet


def get_wallets(db: Session, skip: int = 0, limit: int = 100, account_id: int = None):
    query = db.query(models.Wallet)
    if account_id:
        query = query.filter(models.Wallet.account_id == account_id)
    return query.offset(skip).limit(limit).all()


def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    db_transaction = models.Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def get_transactions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    wallet_id: int = None,
):
    query = db.query(models.Transaction)

    if wallet_id is not None:
        query = query.filter(models.Flow.wallet_id == wallet_id)

    return query.offset(skip).limit(limit).all()


def create_flow(db: Session, flow: schemas.FlowCreate):
    db_flow = models.Flow(**flow.model_dump())
    db.add(db_flow)
    db.commit()
    db.refresh(db_flow)
    return db_flow


def get_flows(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    transaction_id: int = None,
    wallet_id: int = None,
):
    query = db.query(models.Flow)
    if transaction_id is not None:
        query = query.filter(models.Flow.transaction_id == transaction_id)
    if wallet_id is not None:
        query = query.filter(models.Flow.wallet_id == wallet_id)
    return query.offset(skip).limit(limit).all()
