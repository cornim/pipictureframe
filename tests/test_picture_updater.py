import sqlite3
from pathlib import Path

import pytest

from pipictureframe.picdb import get_db
from pipictureframe.picdb.DbObjects import PictureData
from pipictureframe.picdb.PictureUpdater import (
    update_pictures_in_db,
    _add_and_update_pics,
    _clean_db,
)
from pipictureframe.utils.PictureReader import read_pictures_from_disk
from tests.pictures import create_real_picture, get_virtual_pic
from tests.temp_db_manager import TempDbManager


def _count_rows(db_path: Path) -> int:
    con = sqlite3.connect(db_path)
    try:
        return con.execute("SELECT COUNT(*) FROM pictures").fetchone()[0]
    finally:
        con.close()


class TestUpdatePicturesInDb:
    @pytest.fixture
    def conn_str(self, tmp_path: Path):
        db_path = tmp_path / "picture_db.db"
        connection_str = f"sqlite:///{db_path.as_posix()}"
        yield connection_str
        # update_pictures_in_db opens a Database it never closes (in production
        # it runs in a short-lived subprocess). In-process that leaves the
        # classes mapped on the global SQLAlchemy registry, which would break
        # later tests that build a fresh Database. Closing a handle on the same
        # db resets that global state and keeps the suite order-independent.
        get_db(connection_str).close()

    def test_adds_all_pictures_from_directory(self, tmp_path: Path, conn_str: str):
        create_real_picture(tmp_path, "pic1.jpg")
        create_real_picture(tmp_path, "pic2.jpg")
        create_real_picture(tmp_path, "pic3.jpg")
        db_path = tmp_path / "picture_db.db"

        update_pictures_in_db(str(tmp_path), conn_str)

        assert _count_rows(db_path) == 3

    def test_removes_entries_for_deleted_files(self, tmp_path: Path, conn_str: str):
        pic1 = create_real_picture(tmp_path, "pic1.jpg")
        create_real_picture(tmp_path, "pic2.jpg")
        db_path = tmp_path / "picture_db.db"

        update_pictures_in_db(str(tmp_path), conn_str)
        assert _count_rows(db_path) == 2

        # Delete a file and re-run; the stale row must be cleaned up.
        Path(pic1).unlink()
        update_pictures_in_db(str(tmp_path), conn_str)

        assert _count_rows(db_path) == 1


class TestAddAndUpdatePics:
    def test_adds_new_pictures_and_is_idempotent(self, tmp_path: Path):
        create_real_picture(tmp_path, "pic1.jpg")
        create_real_picture(tmp_path, "pic2.jpg")
        with TempDbManager() as test_db:
            session = test_db.db.get_session()
            changed = _add_and_update_pics(
                read_pictures_from_disk(str(tmp_path)), session
            )
            assert changed is True
            assert session.query(PictureData).count() == 2

            # Re-running over the same, unchanged files reports no changes.
            changed_again = _add_and_update_pics(
                read_pictures_from_disk(str(tmp_path)), session
            )
            assert changed_again is False
            assert session.query(PictureData).count() == 2
            session.close()


class TestCleanDb:
    def test_deletes_rows_whose_files_are_missing(self, tmp_path: Path):
        present = create_real_picture(tmp_path, "present.jpg")
        with TempDbManager() as test_db:
            session = test_db.db.get_session()
            _add_and_update_pics(read_pictures_from_disk(str(tmp_path)), session)
            assert session.query(PictureData).count() == 1

            # Add a row pointing at a file that does not exist on disk.
            missing = get_virtual_pic()
            missing.absolute_path = str(tmp_path / "gone.jpg")
            session.add(missing)
            session.commit()
            assert session.query(PictureData).count() == 2

            changed = _clean_db(session)
            assert changed is True
            remaining = session.query(PictureData).all()
            assert len(remaining) == 1
            assert remaining[0].absolute_path == str(present)
            session.close()
