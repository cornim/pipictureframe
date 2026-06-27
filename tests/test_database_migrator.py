from datetime import datetime

from pipictureframe.picdb.Database import (
    Database,
    CURRENT_DB_VERSION,
    LAST_DB_UPDATE_KEY_STR,
    VERSION_STRING,
)
from pipictureframe.picdb.DatabaseMigrator import DatabaseMigrator
from pipictureframe.picdb.DbObjects import Metadata

# The version 1 schema stored last_db_update without sub-second precision.
V1_UPDATE_FMT_STR = "%Y-%m-%d %H:%M:%S"


def _make_db():
    return Database("sqlite:///:memory:", expire_on_commit=False)


def _set_metadata(db, key, value):
    session = db.get_session()
    session.merge(Metadata(key, value))
    session.commit()
    session.close()


def _get_metadata(db, key):
    session = db.get_session()
    value = session.query(Metadata).filter(Metadata.key == key).one().value
    session.close()
    return value


class TestDatabaseMigrator:
    def test_migrate_v1_to_v2_sets_version_and_rewrites_update_time(self):
        db = _make_db()
        try:
            # Simulate a version 1 database: version "1" and a last_db_update
            # stored in the old (no microseconds) format.
            _set_metadata(db, VERSION_STRING, "1")
            _set_metadata(
                db,
                LAST_DB_UPDATE_KEY_STR,
                datetime(2021, 2, 20, 10, 15, 34).strftime(V1_UPDATE_FMT_STR),
            )

            DatabaseMigrator().migrate_to(db, 1, CURRENT_DB_VERSION)

            assert _get_metadata(db, VERSION_STRING) == "2"
            # The update time is now stored in the new format, so reading it back
            # through get_last_update_time parses without raising.
            assert isinstance(db.get_last_update_time(), datetime)
        finally:
            db.close()

    def test_migrate_to_same_version_does_nothing(self):
        db = _make_db()
        try:
            _set_metadata(db, VERSION_STRING, "2")
            # range(2, 2) is empty, so no migration function is invoked.
            DatabaseMigrator().migrate_to(db, 2, 2)
            assert _get_metadata(db, VERSION_STRING) == "2"
        finally:
            db.close()
