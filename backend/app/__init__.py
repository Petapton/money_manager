import os

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/accounts/", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_account(db=db, account=account)
    except IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account name already exists",
            ) from e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e


@app.get("/accounts/", response_model=list[schemas.Account])
def read_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_accounts(db, skip=skip, limit=limit)


@app.post("/wallets/", response_model=schemas.Wallet)
def create_wallet(wallet: schemas.WalletCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_wallet(db=db, wallet=wallet)
    except IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Wallet name already exists for this account",
            ) from e
        if "FOREIGN KEY" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
            ) from e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e


@app.get("/wallets/", response_model=list[schemas.Wallet])
def read_wallets(
    skip: int = 0,
    limit: int = 100,
    account_id: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_wallets(db, skip=skip, limit=limit, account_id=account_id)


@app.post("/transactions/", response_model=schemas.Transaction)
def create_transaction(
    transaction: schemas.TransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transaction(db=db, transaction=transaction)


@app.get("/transactions/", response_model=list[schemas.Transaction])
def read_transactions(
    skip: int = 0,
    limit: int = 100,
    wallet_id: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_transactions(db, skip=skip, limit=limit, wallet_id=wallet_id)


@app.post("/flows/", response_model=schemas.Flow)
def create_flow(flow: schemas.FlowCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_flow(db=db, flow=flow)
    except IntegrityError as e:
        if "FOREIGN KEY" in str(e):
            if "wallet_id" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
                ) from e
            if "transaction_id" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Transaction not found",
                ) from e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e


@app.get("/flows/", response_model=list[schemas.Flow])
def read_flows(
    skip: int = 0,
    limit: int = 100,
    transaction_id: int = None,
    wallet_id: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_flows(
        db, skip=skip, limit=limit, transaction_id=transaction_id, wallet_id=wallet_id
    )
