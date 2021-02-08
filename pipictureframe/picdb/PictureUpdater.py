import logging
import os
from datetime import datetime

from sqlalchemy.orm import Session

from pipictureframe.picdb.Database import (
    Database,
    LAST_DB_UPDATE_KEY_STR,
    LAST_DB_UPDATE_FMT_STR,
)
from pipictureframe.picdb.DbObjects import PictureData, Metadata
from pipictureframe.utils.PictureReader import read_pictures_from_disk, PictureFile

log = logging.getLogger(__name__)


def update_pictures_in_db(pic_dir: str, connections_str: str):
    pic_file_gen = read_pictures_from_disk(pic_dir)
    db = Database(connections_str)

    session = db.get_session()
    db_changed = _clean_db(session)
    db_changed = _add_and_update_pics(pic_file_gen, session) or db_changed
    if db_changed:
        update_obj = Metadata(
            LAST_DB_UPDATE_KEY_STR, datetime.now().strftime(LAST_DB_UPDATE_FMT_STR)
        )
        session.merge(update_obj)
        session.commit()
    session.close()


def _clean_db(session) -> bool:
    db_changed = False
    all_pics = session.query(PictureData).all()
    for pic in all_pics:
        if not os.path.exists(pic.absolute_path):
            session.delete(pic)
            session.commit()
            db_changed = True
    return db_changed


def _add_and_update_pics(pic_file_gen, session) -> bool:
    db_changed = False
    for pic_file in pic_file_gen:
        pic_by_path = _get_pic_by_path(session, pic_file)
        # Is present
        if pic_by_path:
            # Has been modified
            if pic_by_path.mtime < pic_file.mtime:
                log.debug(f"Updated timestamp detected for {pic_file.path}")
                pic_data = PictureData.from_picture_file(pic_file)
                pic_by_hash = _get_pic_by_hash(session, pic_data.hash_id)
                # If modified but hash has not changed
                if pic_by_hash:
                    log.debug(f"Metadata but not hash has changed for {pic_file.path}")
                    session.merge(pic_data)
                # If hash has changed
                else:
                    log.debug(f"Hash has changed for {pic_file.path}")
                    session.delete(pic_by_path)
                    session.add(pic_data)
        # If not present
        else:
            pic_data = PictureData.from_picture_file(pic_file)
            pic_by_hash = _get_pic_by_hash(session, pic_data.hash_id)
            if pic_by_hash:
                log.debug(
                    f"Picture has moved from {pic_by_hash.absolute_path} to {pic_data.absolute_path}"
                )
                session.merge(pic_data)
            else:
                log.debug(f"Picture {pic_file.path} will be added to the database.")
                session.add(pic_data)
        session.commit()
        db_changed = True
    return db_changed


def _get_pic_by_path(session: Session, pic_file: PictureFile) -> PictureData:
    q = session.query(PictureData).filter(PictureData.absolute_path == pic_file.path)
    return q.first()


def _get_pic_by_hash(session: Session, hash_id: str) -> PictureData:
    q = session.query(PictureData).filter(PictureData.hash_id == hash_id)
    return q.first()
