from datetime import datetime

from pipictureframe.picdb.DbObjects import Metadata, PictureData


def _make_picture_data(orig_datetime, mtime):
    return PictureData(
        hash_id="abc",
        abs_path="/tmp/pic.jpg",
        mtime=mtime,
        orig_datetime=orig_datetime,
        orientation=1,
        rating=3,
        lat_ref="N",
        lat=50.34,
        long_ref="E",
        long=8.53,
    )


class TestPictureDataGetDateTime:
    def test_returns_original_date_time_when_present(self):
        orig = datetime(2021, 2, 20, 10, 15, 34)
        pic = _make_picture_data(orig_datetime=orig, mtime=1613744460.72)
        assert pic.get_date_time() == orig

    def test_falls_back_to_mtime_when_original_missing(self):
        mtime = 1613744460.72
        pic = _make_picture_data(orig_datetime=None, mtime=mtime)
        assert pic.get_date_time() == datetime.fromtimestamp(mtime)

    def test_times_shown_defaults_to_zero(self):
        pic = _make_picture_data(orig_datetime=None, mtime=1.0)
        assert pic.times_shown == 0


class TestMetadata:
    def test_stores_key_and_value(self):
        md = Metadata("last_update", "2021-02-20")
        assert md.key == "last_update"
        assert md.value == "2021-02-20"

    def test_repr_contains_key_and_value(self):
        md = Metadata("k", "v")
        text = repr(md)
        assert "k" in text and "v" in text
