from datetime import datetime
from typing import List

from pipictureframe.picdb.Database import (
    Database,
    LAST_DB_UPDATE_KEY_STR,
    LAST_DB_UPDATE_FMT_STR,
)
from pipictureframe.picdb.DbObjects import PictureData, Metadata
from tests.pictures import PictureGenerator


class DbManager:
    def __init__(self):
        self.db = Database("sqlite:///:memory:", expire_on_commit=False)

    def load_db(self, pic_list: List[PictureData]):
        session = self.db.get_session()
        for pic in pic_list:
            session.add(pic)
        session.commit()
        session.close()

    def load_n_random_pictures(self, n: int):
        pg = PictureGenerator()
        pics = []
        for i in range(n):
            pics.append(pg.get_default_pic())
        self.load_db(pics)
        return pics

    def set_db_update_time(self, update_time: datetime):
        session = self.db.get_session()
        session.merge(
            Metadata(
                LAST_DB_UPDATE_KEY_STR, update_time.strftime(LAST_DB_UPDATE_FMT_STR)
            )
        )
        session.commit()
        session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
