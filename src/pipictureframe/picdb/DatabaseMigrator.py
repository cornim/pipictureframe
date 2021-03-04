from datetime import datetime

from pipictureframe.picdb.Database import (
    Database,
    LAST_DB_UPDATE_KEY_STR,
    VERSION_STRING,
)
from pipictureframe.picdb.DbObjects import Metadata


def _version_1_to_2(db: Database):
    session = db.get_session()
    last_db_update = datetime.strptime(
        session.query(Metadata)
        .filter(Metadata.key == LAST_DB_UPDATE_KEY_STR)
        .one()
        .value,
        "%Y-%m-%d %H:%M:%S",
    )
    db.set_last_update_time(last_db_update, session)
    session.merge(Metadata(VERSION_STRING, "2"))
    session.commit()
    session.close()


class DatabaseMigrator:
    def __init__(self):
        self.migration_functions = dict()
        self.migration_functions[1] = _version_1_to_2

    def migrate_to(self, db: Database, current_version: int, new_version: int):
        for i in range(current_version, new_version):
            self.migration_functions[i](db)
