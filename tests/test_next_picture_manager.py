from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from tests.db_manager import DbManager
from pipictureframe.utils.NextPictureManager import NextPictureManager
from tests.mocks import get_config_mock
from tests.pictures import PictureGenerator


def setup_module(module):
    patcher = patch("os.path.exists")
    mock_thing = patcher.start()
    mock_thing.side_effect = lambda path: False if "_ne_" in path else True


def test_npm_one_pic_no_shuffle():
    config = get_config_mock()
    with DbManager() as test_db:
        pics = test_db.load_n_random_pictures(1)
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        npm = NextPictureManager(config, proc, test_db.db)
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pics[0].hash_id


def test_npm_four_pics_no_shuffle():
    config = get_config_mock()
    proc = Mock()
    proc.is_alive = Mock(return_value=False)
    with DbManager() as test_db:
        pg = PictureGenerator()
        pic1 = pg.get_default_pic()
        pic1.orig_date_time = datetime(2020, 1, 1)
        pic2 = pg.get_default_pic()
        pic2.orig_date_time = datetime(2020, 2, 1)
        pic3 = pg.get_default_pic()
        pic3.orig_date_time = datetime(2020, 3, 1)
        pics = [pic1, pic2, pic3]
        test_db.load_db(pics)
        npm = NextPictureManager(config, proc, test_db.db)
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pics[0].hash_id
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pics[1].hash_id
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pics[2].hash_id


def test_npm_no_pics():
    config = get_config_mock()
    with DbManager() as test_db:
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            NextPictureManager(config, proc, test_db.db)
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1


def test_npm_end_of_list():
    config = get_config_mock()
    proc = Mock()
    proc.is_alive = Mock(return_value=False)
    with DbManager() as test_db:
        pg = PictureGenerator()
        pic1 = pg.get_default_pic()
        pic1.orig_date_time = datetime(2020, 1, 1)
        pic2 = pg.get_default_pic()
        pic2.orig_date_time = datetime(2020, 2, 1)
        pics = [pic1, pic2]
        test_db.load_db(pics)
        test_db.set_db_update_time(datetime(2019, 1, 1))
        npm = NextPictureManager(config, proc, test_db.db)

        pic3 = pg.get_default_pic()
        pic3.orig_date_time = datetime(2020, 3, 1)
        test_db.load_db([pic3])
        test_db.set_db_update_time(datetime(2020, 1, 1))
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pic1.hash_id
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pic2.hash_id
        npm.get_next_picture()
        npm.get_next_picture()
        cur_pic = npm.get_next_picture()
        assert cur_pic.hash_id == pic3.hash_id
