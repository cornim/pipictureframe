from datetime import datetime, timedelta
from hashlib import md5
from pathlib import Path
from random import choices, random as rnd_float
from string import ascii_lowercase

from PIL import Image

from pipictureframe.picdb.DbObjects import PictureData


def create_real_picture(dir_path: Path, name: str = None):
    img = Image.new(
        "RGB",
        (80, 60),
        color=(int(rnd_float() * 255), int(rnd_float() * 255), int(rnd_float() * 255)),
    )
    if not name:
        name = "".join(choices(ascii_lowercase, k=20)) + ".jpg"
    file_path = Path(dir_path, name)
    img.save(file_path)
    return file_path


def get_virtual_pic(random: bool = True):
    hash_str: str = "a"
    abs_path: str = "/home/pi/Pictures/test1.jpg"
    mtime: float = 1613744460.720702
    orig_datetime: datetime = datetime(2021, 2, 20, 10, 15, 34)
    orientation: int = 1
    rating: int = 3
    lat_ref: str = "N"
    lat: float = 50.34
    long_ref: str = "E"
    long: float = 8.5345
    times_shown: int = 3

    if random:
        hash_str = "".join(choices(ascii_lowercase, k=20))
        abs_path = f"/home/pi/Pictures/{''.join(choices(ascii_lowercase, k=10))}.jpg"
        mtime += rnd_float()
        orig_datetime += timedelta(rnd_float() * 10)

    hash_id = md5(hash_str.encode()).hexdigest()
    pic = PictureData(
        hash_id,
        abs_path,
        mtime,
        orig_datetime,
        orientation,
        rating,
        lat_ref,
        lat,
        long_ref,
        long,
        times_shown,
    )
    return pic
