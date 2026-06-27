from datetime import datetime
from typing import List
from unittest.mock import Mock, PropertyMock

from pipictureframe.picdb.Database import LAST_DB_UPDATE_FMT_STR
from pipictureframe.picdb.DbObjects import PictureData, Metadata

dt_now = datetime.now()


def get_config_mock(
    shuffle=False, shuffle_weight=0, reshuffle_num=1, min_rating=None, max_rating=None
):
    config = Mock()
    config.shuffle = PropertyMock()
    config.shuffle = shuffle
    config.shuffle_weight = PropertyMock()
    config.shuffle_weight = shuffle_weight
    config.reshuffle_num = PropertyMock()
    config.reshuffle_num = reshuffle_num
    config.min_rating = PropertyMock()
    config.min_rating = min_rating
    config.max_rating = PropertyMock()
    config.max_rating = max_rating
    return config


def get_db_mock(return_pics: List[PictureData], update_time=dt_now):
    query = Mock()
    query.filter = Mock(return_value=query)
    query.all = Mock(return_value=return_pics)
    query.one = Mock(
        return_value=Metadata("x", update_time.strftime(LAST_DB_UPDATE_FMT_STR))
    )
    session = Mock()
    session.query = Mock(return_value=query)
    db = Mock()
    db.get_session = Mock(return_value=session)
    return db
