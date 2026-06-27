import logging
import os
import random
import sys
import time
from datetime import datetime
from typing import List, Optional
from multiprocessing import Process

from pipictureframe.picdb.Database import Database
from pipictureframe.picdb.DbObjects import PictureData

FILTER_RATING_BELOW = "frb"
FILTER_RATING_ABOVE = "fra"

log = logging.getLogger(__name__)


class NextPictureManager:
    def __init__(self, config, pic_load_bg_proc: Process, db: Database):
        self.config = config
        self.pic_load_bg_proc = pic_load_bg_proc
        self.filters = dict()
        # Use "is not None" so a rating threshold of 0 is honoured. A plain
        # truthiness check silently dropped the filter when the limit was 0.
        if config.min_rating is not None:
            self.filters[FILTER_RATING_BELOW] = config.min_rating
        if config.max_rating is not None:
            self.filters[FILTER_RATING_ABOVE] = config.max_rating

        self.db = db
        self.last_db_update = datetime(1, 1, 1)

        self.cur_pic_num = 0
        self.times_through = 0
        self.sample_list = None
        self.reload_pictures()

    def get_next_picture(self):
        # Loop (rather than recurse) so a long run of missing files cannot
        # blow the Python recursion limit.
        while True:
            if self.cur_pic_num >= len(self.sample_list):
                self.times_through += 1
                # Pick up database changes first; a reload also re-orders the
                # list. If nothing changed, reshuffle every reshuffle_num passes
                # so a shuffled slideshow does not repeat the same order forever.
                reloaded = self.reload_pictures()
                self.cur_pic_num = 0
                if not reloaded and self.config.shuffle:
                    reshuffle_num = max(1, self.config.reshuffle_num)
                    if self.times_through % reshuffle_num == 0:
                        log.debug(
                            f"Reshuffling picture list after "
                            f"{self.times_through} passes."
                        )
                        self._order_sample_list()
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
                log.debug(
                    f"{cur_pic.absolute_path} no longer exists on disk; skipping."
                )

    def _inc_times_shown(self, cur_pic):
        session = self.db.get_session()
        cur_pic.times_shown += 1
        session.merge(cur_pic)
        session.commit()
        session.close()

    def reload_pictures(self) -> bool:
        """Reload the picture list from the database if it has changed.

        Returns True when the in-memory list was replaced with a freshly loaded
        (and re-ordered) list, and False when no database update was detected.
        """
        full_picture_list = self._load_pictures_from_db()
        if full_picture_list is None:
            log.debug("No update in db detected. Keeping current picture list.")
            return False

        if len(full_picture_list) == 0:
            if self.pic_load_bg_proc.is_alive():
                # Give the bg process some time to load pictures into the database
                time.sleep(10)
                return self.reload_pictures()
            else:
                log.fatal("No pictures found to display in database.")
                sys.exit(1)
        else:
            self.sample_list = full_picture_list
            self.cur_pic_num = 0
            self._order_sample_list()
            return True

    def _order_sample_list(self):
        """Sort or (optionally weighted-)shuffle self.sample_list in place."""
        if not self.config.shuffle:
            self.sample_list.sort(key=lambda x: x.get_date_time())
        elif self.config.shuffle_weight == 0:
            random.shuffle(self.sample_list)
        else:
            nums_shown = [pic.times_shown for pic in self.sample_list]
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
                self.sample_list, weights=weights, k=len(self.sample_list)
            )
            log.debug(
                f"The first 100 pictures out of {len(self.sample_list)} are "
                f"{[x.absolute_path for x in self.sample_list[:100]]}."
            )

    def _load_pictures_from_db(self) -> Optional[List[PictureData]]:
        last_db_update = self.db.get_last_update_time()
        log.debug(
            f"Last update in NextPicture manager = {self.last_db_update} and "
            f"last update of db = {last_db_update}"
        )
        if self.last_db_update < last_db_update:
            session = self.db.get_session()
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
