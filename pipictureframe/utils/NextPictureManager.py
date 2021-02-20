import logging
import os
import random
import time
from datetime import datetime
from typing import List, Optional
from multiprocessing import Process

from pipictureframe.picdb.Database import (
    Database,
    LAST_DB_UPDATE_KEY_STR,
    LAST_DB_UPDATE_FMT_STR,
)
from pipictureframe.picdb.DbObjects import Metadata
from pipictureframe.picdb.PictureUpdater import PictureData

FILTER_RATING_BELOW = "frb"
FILTER_RATING_ABOVE = "fra"

log = logging.getLogger(__name__)


class NextPictureManager:
    def __init__(self, config, pic_load_bg_proc: Process, db: Database):
        self.config = config
        self.pic_load_bg_proc = pic_load_bg_proc
        self.filters = dict()
        if config.min_rating:
            self.filters[FILTER_RATING_BELOW] = config.min_rating
        if config.max_rating:
            self.filters[FILTER_RATING_ABOVE] = config.max_rating

        self.db = db
        self.last_db_update = datetime(1, 1, 1)

        self.cur_pic_num = 0
        self.sample_list = None
        self.reload_pictures()

    def get_next_picture(self):
        if self.cur_pic_num >= len(self.sample_list):
            self.reload_pictures()
        cur_pic: PictureData = self.sample_list[self.cur_pic_num]
        self.cur_pic_num += 1
        if os.path.exists(cur_pic.absolute_path):
            self._inc_times_shown(cur_pic)
            log.debug(
                f"{cur_pic.absolute_path} chosen to be shown as next picture. "
                f"Current picture number is {self.cur_pic_num}."
            )
            return cur_pic
        else:
            return self.get_next_picture()

    def _inc_times_shown(self, cur_pic):
        session = self.db.get_session()
        cur_pic.times_shown += 1
        session.merge(cur_pic)
        session.commit()
        session.close()

    def reload_pictures(self):
        full_picture_list = self._load_pictures_from_db()
        if full_picture_list is None:
            log.debug("No update in db detected. Keeping current picture list.")
            return self.sample_list
        if len(full_picture_list) == 0:
            if self.pic_load_bg_proc.is_alive():
                time.sleep(
                    10
                )  # Give the bg process some time to load pictures into the database
                self.reload_pictures()
            else:
                log.fatal("No pictures found to display in database.")
                exit(1)

        self.sample_list = full_picture_list
        self.cur_pic_num = 0
        if not self.config.shuffle:
            self.sample_list.sort(key=lambda x: x.get_date_time())
        elif self.config.shuffle_weight == 0:
            random.shuffle(self.sample_list)
        else:
            nums_shown = [pic.times_shown for pic in full_picture_list]
            max_num_shown = max(nums_shown)
            weights = [
                (max_num_shown + 1 - x)
                / (max_num_shown + 1)
                * self.config.shuffle_weight
                + 1
                for x in nums_shown
            ]
            log.debug(
                f"The first 100 weights out of {len(weights)} are {weights[:100]}."
            )
            self.sample_list = random.choices(
                full_picture_list, weights=weights, k=len(full_picture_list)
            )
            log.debug(
                f"The first 100 pictures out of {len(self.sample_list)} are "
                f"{[x.absolute_path for x in self.sample_list[:100]]}."
            )

    def _load_pictures_from_db(self) -> Optional[List[PictureData]]:
        session = self.db.get_session()
        last_db_update = datetime.strptime(
            session.query(Metadata)
            .filter(Metadata.key == LAST_DB_UPDATE_KEY_STR)
            .one()
            .value,
            LAST_DB_UPDATE_FMT_STR,
        )
        log.debug(
            f"Last update in NextPicture manager = {self.last_db_update} and "
            f"last update of db = {last_db_update}"
        )
        if self.last_db_update < last_db_update:
            q = session.query(PictureData)
            if FILTER_RATING_BELOW in self.filters:
                q = q.filter(PictureData.rating >= self.filters[FILTER_RATING_BELOW])
            if FILTER_RATING_ABOVE in self.filters:
                q = q.filter(PictureData.rating <= self.filters[FILTER_RATING_ABOVE])
            full_picture_list = q.all()
            log.info(f"{len(full_picture_list)} pictures loaded.")
            session.close()
            self.last_db_update = last_db_update
            return full_picture_list
        else:
            return None
