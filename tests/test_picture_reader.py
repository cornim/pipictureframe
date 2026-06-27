from pathlib import Path

import pytest

from pipictureframe.utils.PictureReader import (
    ExifData,
    PictureFile,
    lazy_property,
    read_pictures_from_disk,
)
from tests.pictures import create_real_picture


class TestConvertGpsTupleToDecimal:
    def test_dms_tuple_is_converted_to_decimal_degrees(self):
        # 50 deg, 20 min, 24 sec -> 50 + 20/60 + 24/3600 = 50.34
        result = ExifData._convert_gps_tuple_to_decimal((50, 20, 24))
        assert result == pytest.approx(50.34)

    def test_non_tuple_value_is_passed_through_unchanged(self):
        assert ExifData._convert_gps_tuple_to_decimal(8.5) == 8.5

    def test_none_is_passed_through(self):
        assert ExifData._convert_gps_tuple_to_decimal(None) is None

    def test_unconvertible_tuple_returns_none(self):
        # Non-numeric components raise inside the conversion and are swallowed,
        # so the method returns None rather than propagating the error.
        assert ExifData._convert_gps_tuple_to_decimal(("a", "b", "c")) is None


class TestLazyProperty:
    def test_value_is_computed_once_and_cached(self):
        class Counter:
            def __init__(self):
                self.calls = 0

            @lazy_property
            def value(self):
                self.calls += 1
                return 42

        c = Counter()
        assert c.calls == 0
        assert c.value == 42
        assert c.value == 42
        assert c.calls == 1

    def test_instances_cache_independently(self):
        class Counter:
            def __init__(self):
                self.calls = 0

            @lazy_property
            def value(self):
                self.calls += 1
                return id(self)

        a = Counter()
        b = Counter()
        assert a.value != b.value
        assert a.calls == 1
        assert b.calls == 1


class TestReadPicturesFromDisk:
    def test_yields_only_image_files_recursively_and_case_insensitively(
        self, tmp_path: Path
    ):
        create_real_picture(tmp_path, "pic1.jpg")
        create_real_picture(tmp_path, "pic2.PNG")
        create_real_picture(tmp_path, "pic3.jpeg")
        sub = tmp_path / "sub"
        sub.mkdir()
        create_real_picture(sub, "pic4.jpg")
        # Non-image files that must be ignored.
        (tmp_path / "notes.txt").write_text("not an image")
        (tmp_path / "skip.gif").write_bytes(b"GIF89a")

        results = list(read_pictures_from_disk(str(tmp_path)))

        assert all(isinstance(p, PictureFile) for p in results)
        names = {Path(p.path).name for p in results}
        assert names == {"pic1.jpg", "pic2.PNG", "pic3.jpeg", "pic4.jpg"}

    def test_empty_directory_yields_nothing(self, tmp_path: Path):
        assert list(read_pictures_from_disk(str(tmp_path))) == []


class TestPictureFile:
    def test_mtime_is_populated_on_construction(self, tmp_path: Path):
        path = create_real_picture(tmp_path, "pic.jpg")
        pic = PictureFile(str(path))
        assert pic.path == str(path)
        assert isinstance(pic.mtime, float)
        assert pic.mtime > 0
