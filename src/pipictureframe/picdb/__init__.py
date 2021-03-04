from pipictureframe.picdb.Database import Database, CURRENT_DB_VERSION
from pipictureframe.picdb.DatabaseMigrator import DatabaseMigrator


def get_db(connection_string: str, echo=False, expire_on_commit=True):
    db = Database(connection_string, echo, expire_on_commit)
    if db.version < CURRENT_DB_VERSION:
        migrator = DatabaseMigrator()
        migrator.migrate_to(db, db.version, CURRENT_DB_VERSION)
    return db
