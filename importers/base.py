from sqlalchemy.orm import Session

from backend.app import models, schemas


class BaseImporter:
    _account_name: str = None
    _wallets = {
        # "wallet_name": {
        #     "name": str,
        #     "currency": schemas.Currency,
        #     "flows": [
        #         {
        #             "type": schemas.Operation,
        #             "date": datetime,
        #             "description": str,
        #             "amount": Decimal,
        #             "state": schemas.State,
        #         }
        #     ]
        # }
    }

    def __init__(self, path: str, db: Session):
        self.path = path
        self.db = db

    def __repr__(self):
        return f"<BaseImporter(path='{self.path}')>"

    def _import_data(self):
        raise NotImplementedError

    def import_data(self):
        self._import_data()

        self.db.begin()
        try:
            self._gen_db_data()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _gen_db_data(self):
        account_db = (
            self.db.query(models.Account).filter_by(name=self._account_name).first()
        )
        if account_db is None:
            account_db = models.Account(name=self._account_name)
            self.db.add(account_db)

        for _, wallet in self._wallets.items():
            wallet_db = models.Wallet(
                name=wallet["name"],
                currency=wallet["currency"],
                account=account_db,
            )

            self.db.add_all(
                [wallet_db]
                + sum(
                    [
                        [
                            transaction_db := models.Transaction(
                                type=flow["type"],
                                date=flow["date"],
                                description=flow["description"],
                            ),
                            models.Flow(
                                amount=flow["amount"],
                                state=flow["state"],
                                wallet=wallet_db,
                                transaction=transaction_db,
                            ),
                        ]
                        for flow in wallet["flows"]
                    ],
                    [],
                )
            )

        self.db.flush()
