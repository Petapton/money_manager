from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, condecimal

from .models import Currency, Operation


class AccountBase(BaseModel):
    name: str = Field(..., max_length=50)


class AccountCreate(AccountBase):
    pass


class Account(AccountBase):
    id: int

    model_config = {"from_attributes": True}


class WalletBase(BaseModel):
    name: str = Field(..., max_length=50)
    currency: Currency


class WalletCreate(WalletBase):
    account_id: int


class Wallet(WalletBase):
    id: int
    account_id: int
    balance: condecimal(max_digits=20, decimal_places=2)

    model_config = {"from_attributes": True}


class TransactionBase(BaseModel):
    type: Operation
    description: Optional[str] = None
    date: datetime


class TransactionCreate(TransactionBase):
    pass


class Transaction(TransactionBase):
    id: int

    model_config = {"from_attributes": True}


class FlowBase(BaseModel):
    amount: condecimal(max_digits=20, decimal_places=2)


class FlowCreate(FlowBase):
    wallet_id: int
    transaction_id: int


class Flow(FlowBase):
    id: int
    wallet_id: int
    transaction_id: int

    model_config = {"from_attributes": True}


class AccountWithWallets(Account):
    wallets: List[Wallet]


class WalletWithFlows(Wallet):
    flows: List[Flow]


class TransactionWithFlows(Transaction):
    flows: List[Flow]
