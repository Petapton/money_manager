import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship

from .database import Base


class Currency(enum.Enum):
    EUR = "EUR"  # Euro
    USD = "USD"  # US Dollar
    GBP = "GBP"  # British Pound


class Operation(enum.Enum):
    DEP = "DEP"  # Deposit
    WDR = "WDR"  # Withdrawal
    TRN = "TRN"  # Transfer
    INC = "INC"  # Income
    PAY = "PAY"  # Payment
    REF = "REF"  # Refund
    BAL = "BAL"  # Balance
    OTH = "OTH"  # Other


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)

    wallets = relationship("Wallet", back_populates="account")

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}')>"


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    currency = Column(Enum(Currency), nullable=False, default=Currency.EUR)

    account = relationship("Account", back_populates="wallets")
    flows = relationship("Flow", back_populates="wallet")

    __table_args__ = (
        UniqueConstraint("name", "account_id", name="unique_wallet_name_for_account"),
    )

    @hybrid_property
    def balance(self):
        return sum(flow.amount for flow in self.flows)

    @balance.expression
    def balance(cls):
        return (
            select(func.coalesce(func.sum(Flow.amount), 0))
            .where(Flow.wallet_id == cls.id)
            .scalar_subquery()
        )

    def __repr__(self):
        return f"<Wallet(id={self.id}, name='{self.name}', currency={self.currency} balance={self.balance}>"


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    type = Column(Enum(Operation), nullable=False)
    date = Column(DateTime)
    description = Column(Text)

    flows = relationship("Flow", back_populates="transaction")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.type}, date='{self.date}')>"

    class Config:
        orm_mode = True


class Flow(Base):
    __tablename__ = "flows"
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    amount = Column(Numeric(20, 2))
    transaction_id = Column(Integer, ForeignKey("transactions.id"))

    wallet = relationship("Wallet", back_populates="flows")
    transaction = relationship("Transaction", back_populates="flows")

    def __repr__(self):
        return f"<Flow(id={self.id}, amount={self.amount})>"

    class Config:
        orm_mode = True
