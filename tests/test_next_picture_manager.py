from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from pipictureframe.utils.NextPictureManager import NextPictureManager
from tests.temp_db_manager import TempDbManager
from tests.mocks import get_config_mock
from tests.pictures import get_virtual_pic


class TestNextPictureManager:
    @pytest.fixture(scope="class", autouse=True)
    def setup_module(self):
        patcher = patch("os.path.exists")
        mock_thing = patcher.start()
        mock_thing.side_effect = lambda path: False if "_ne_" in path else True
        yield
        patcher.stop()

    def test_npm_one_pic_no_shuffle(self):
        config = get_config_mock()
        with TempDbManager() as test_db:
            pics = test_db.load_n_random_pictures(1)
            proc = Mock()
            proc.is_alive = Mock(return_value=False)
            npm = NextPictureManager(config, proc, test_db.db)
            cur_pic = npm.get_next_picture()
            assert cur_pic.hash_id == pics[0].hash_id

    def test_npm_max_rating_zero_is_applied(self):
        # A max_rating of 0 must filter out higher rated pictures. The previous
        # truthiness check treated 0 as "no filter" and returned everything.
        config = get_config_mock(max_rating=0)
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            low = get_virtual_pic()
            low.rating = 0
            low.orig_date_time = datetime(2020, 1, 1)
            high = get_virtual_pic()
            high.rating = 3
            high.orig_date_time = datetime(2020, 2, 1)
            test_db.load_db([low, high])
            npm = NextPictureManager(config, proc, test_db.db)
            assert [p.hash_id for p in npm.sample_list] == [low.hash_id]

    def test_npm_min_rating_zero_is_applied(self):
        # A min_rating of 0 must exclude unrated (-1) pictures.
        config = get_config_mock(min_rating=0)
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            unrated = get_virtual_pic()
            unrated.rating = -1
            unrated.orig_date_time = datetime(2020, 1, 1)
            rated = get_virtual_pic()
            rated.rating = 0
            rated.orig_date_time = datetime(2020, 2, 1)
            test_db.load_db([unrated, rated])
            npm = NextPictureManager(config, proc, test_db.db)
            assert [p.hash_id for p in npm.sample_list] == [rated.hash_id]

    def test_npm_four_pics_no_shuffle(self):
        config = get_config_mock()
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            pic1 = get_virtual_pic()
            pic1.orig_date_time = datetime(2020, 1, 1)
            pic2 = get_virtual_pic()
            pic2.orig_date_time = datetime(2020, 2, 1)
            pic3 = get_virtual_pic()
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

    def test_npm_no_pics(self):
        config = get_config_mock()
        with TempDbManager() as test_db:
            proc = Mock()
            proc.is_alive = Mock(return_value=False)
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                NextPictureManager(config, proc, test_db.db)
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 1

    def test_npm_end_of_list(self):
        config = get_config_mock()
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            pic1 = get_virtual_pic()
            pic1.orig_date_time = datetime(2020, 1, 1)
            pic2 = get_virtual_pic()
            pic2.orig_date_time = datetime(2020, 2, 1)
            pics = [pic1, pic2]
            test_db.load_db(pics)
            test_db.set_db_update_time(datetime(2019, 1, 1))
            npm = NextPictureManager(config, proc, test_db.db)

            pic3 = get_virtual_pic()
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

    def test_npm_skips_many_missing_files_without_recursion(self):
        # More entries than the default recursion limit so the previous
        # recursive implementation would raise RecursionError.
        config = get_config_mock()
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            pics = []
            for i in range(1500):
                pic = get_virtual_pic()
                pic.absolute_path = f"/home/pi/Pictures/_ne_missing_{i:05d}.jpg"
                pic.orig_date_time = datetime(2020, 1, 1) + timedelta(seconds=i)
                pics.append(pic)
            present = get_virtual_pic()
            present.absolute_path = "/home/pi/Pictures/present.jpg"
            present.orig_date_time = datetime(2020, 12, 31)
            pics.append(present)
            test_db.load_db(pics)

            npm = NextPictureManager(config, proc, test_db.db)
            cur_pic = npm.get_next_picture()
            assert cur_pic.absolute_path == present.absolute_path

    def _load_stable_db(self, test_db, n):
        pics = [get_virtual_pic() for _ in range(n)]
        test_db.load_db(pics)
        # Fix the db update time in the past so reload_pictures reports "no
        # change" once the list has been loaded the first time.
        test_db.set_db_update_time(datetime(2000, 1, 1))
        return pics

    def test_reshuffles_every_pass_when_reshuffle_num_is_1(self):
        config = get_config_mock(shuffle=True, reshuffle_num=1)
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            pics = self._load_stable_db(test_db, 3)
            with patch(
                "pipictureframe.utils.NextPictureManager.random.shuffle"
            ) as shuffle_mock:
                npm = NextPictureManager(config, proc, test_db.db)
                # Initial ordering shuffles once.
                assert shuffle_mock.call_count == 1
                for _ in range(len(pics)):
                    npm.get_next_picture()
                # Crossing the pass boundary reshuffles again.
                npm.get_next_picture()
                assert shuffle_mock.call_count == 2

    def test_reshuffles_every_second_pass_when_reshuffle_num_is_2(self):
        config = get_config_mock(shuffle=True, reshuffle_num=2)
        proc = Mock()
        proc.is_alive = Mock(return_value=False)
        with TempDbManager() as test_db:
            pics = self._load_stable_db(test_db, 3)
            with patch(
                "pipictureframe.utils.NextPictureManager.random.shuffle"
            ) as shuffle_mock:
                npm = NextPictureManager(config, proc, test_db.db)
                assert shuffle_mock.call_count == 1
                # First full pass + boundary: 1 % 2 != 0, no reshuffle.
                for _ in range(len(pics)):
                    npm.get_next_picture()
                npm.get_next_picture()
                assert shuffle_mock.call_count == 1
                # Second full pass + boundary: 2 % 2 == 0, reshuffle.
                for _ in range(len(pics) - 1):
                    npm.get_next_picture()
                npm.get_next_picture()
                assert shuffle_mock.call_count == 2
