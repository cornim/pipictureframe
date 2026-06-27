from sqlalchemy import text

from pipictureframe.picdb.Database import Database


class TestSqliteConcurrency:
    def test_wal_and_busy_timeout_set_on_file_db(self, tmp_path):
        # WAL mode is only meaningful for an on-disk database, so use a file.
        db_path = tmp_path / "picture_db.db"
        db = Database(f"sqlite:///{db_path.as_posix()}", expire_on_commit=False)
        try:
            with db.engine.connect() as conn:
                journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
                busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
            assert str(journal_mode).lower() == "wal"
            assert int(busy_timeout) == 30000
        finally:
            db.close()
