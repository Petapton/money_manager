import csv
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, validator
from slugify import slugify

from backend.app import schemas

from .base import BaseImporter


class Type(Enum):
    TOPUP = "TOPUP"
    CARD_PAYMENT = "CARD_PAYMENT"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    EXCHANGE = "EXCHANGE"
    CARD_CREDIT = "CARD_CREDIT"
    CARD_REFUND = "CARD_REFUND"
    FEE = "FEE"


class State(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVERTED = "REVERTED"


class RevolutFlow(BaseModel):
    type: Type
    product: str
    started_date: datetime
    completed_date: Optional[datetime]
    description: str
    amount: Decimal
    fee: Decimal
    currency: schemas.Currency
    state: State
    balance: Optional[Decimal]

    @validator("completed_date", "balance", pre=True)
    def parse_completed_date(cls, v):
        return None if v == "" else v


_type_map = {
    Type.TOPUP: schemas.Operation.DEP,
    Type.CARD_PAYMENT: schemas.Operation.PAY,
    Type.TRANSFER: schemas.Operation.TRN,
    Type.REFUND: schemas.Operation.REF,
    Type.EXCHANGE: schemas.Operation.TRN,
    Type.CARD_CREDIT: schemas.Operation.INC,
    Type.CARD_REFUND: schemas.Operation.REF,
    Type.FEE: schemas.Operation.PAY,
}


_state_map = {
    State.PENDING: schemas.State.PDG,
    State.COMPLETED: schemas.State.CPL,
    State.REVERTED: schemas.State.RVT,
}


class RevolutImporter(BaseImporter):
    _account_name = "Revolut"

    def _import_data(self):
        with open(self.path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            flows = [
                RevolutFlow(**{slugify(k, separator="_"): v for k, v in row.items()})
                for row in reader
            ]

        for flow in flows:
            if f"{flow.product} ({flow.currency})" not in self._wallets:
                self._wallets[f"{flow.product} ({flow.currency})"] = {
                    "name": f"{flow.product} ({flow.currency})",
                    "currency": flow.currency,
                    "flows": [],
                }

            self._wallets[f"{flow.product} ({flow.currency})"]["flows"].append(
                {
                    "type": _type_map[flow.type],
                    "date": flow.started_date,
                    "description": flow.description,
                    "amount": flow.amount,
                    "state": _state_map[flow.state],
                }
            )
            if flow.fee:
                self._wallets[f"{flow.product} ({flow.currency})"]["flows"].append(
                    {
                        "type": schemas.Operation.PAY,
                        "date": flow.started_date,
                        "description": "Fee",
                        "amount": -flow.fee,
                        "state": _state_map[flow.state],
                    }
                )
