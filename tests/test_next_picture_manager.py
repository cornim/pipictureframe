from unittest.mock import Mock
from datetime import datetime

import pytest

from pipictureframe.picdb.PictureUpdater import PictureData
from pipictureframe.utils.NextPictureManager import NextPictureManager
from tests.mocks import get_config_mock, get_db_mock


pic1 = PictureData(
    "xxx",
    "/home/pi/photos/ab.jpg",
    20,
    datetime(2020, 1, 2),
    0,
    1,
    None,
    None,
    None,
    None,
)

pic2 = PictureData(
    "xxy",
    "/home/pi/photos/abc.jpg",
    21,
    datetime(2020, 1, 3),
    0,
    2,
    None,
    None,
    None,
    None,
)

pic3 = PictureData(
    "xxz",
    "/home/pi/photos/abd.jpg",
    22,
    datetime(2020, 1, 4),
    0,
    3,
    None,
    None,
    None,
    None,
)

pic4 = PictureData(
    "xxa",
    "/home/pi/photos/abe.jpg",
    23,
    datetime(2020, 1, 5),
    0,
    4,
    None,
    None,
    None,
    None,
)


def test_npm_one_pic_no_shuffle():
    config = get_config_mock()
    db = get_db_mock([pic1])
    proc = Mock()
    proc.is_alive = Mock(return_value=False)
    npm = NextPictureManager(config, proc, db)
    cur_pic = npm.get_next_picture()
    assert cur_pic == pic1


def test_npm_four_pics_no_shuffle():
    config = get_config_mock()
    db = get_db_mock([pic1, pic2, pic3, pic4])
    proc = Mock()
    proc.is_alive = Mock(return_value=False)
    npm = NextPictureManager(config, proc, db)
    cur_pic = npm.get_next_picture()
    assert cur_pic == pic1
    cur_pic = npm.get_next_picture()
    assert cur_pic == pic2
    cur_pic = npm.get_next_picture()
    assert cur_pic == pic3


def test_npm_no_pics():
    config = get_config_mock()
    db = get_db_mock([])
    proc = Mock()
    proc.is_alive = Mock(return_value=False)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        NextPictureManager(config, proc, db)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


def test_npm_end_of_list():
    config = get_config_mock()
    db = get_db_mock([pic1, pic2])
    proc = Mock()
    proc.is_alive = Mock(return_value=False)
    npm = NextPictureManager(config, proc, db)
    cur_pic = npm.get_next_picture()
    npm.db = get_db_mock([pic4])
    assert cur_pic == pic1
    cur_pic = npm.get_next_picture()
    assert cur_pic == pic2
    cur_pic = npm.get_next_picture()
    assert cur_pic == pic4
