import argparse

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base

from . import formats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import data from various sources")
    parser.add_argument(
        "format", type=str, choices=formats.keys(), help="The format of the data file"
    )
    parser.add_argument("path", type=str, help="The path to the data file")
    parser.add_argument(
        "--database",
        type=str,
        default="sqlite:///./data.db",
        help="The database connection string",
    )
    args = parser.parse_args()

    engine = create_engine(args.database)

    if engine.url.drivername == "sqlite":

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        importer = formats[args.format](args.path, db)
        importer.import_data()
