from datetime import datetime

from pipictureframe.utils.PictureReader import PictureFile


class PictureData:
    def __init__(
        self,
        hash_id: str,
        abs_path: str,
        mtime: int,
        orig_datetime: datetime,
        orientation: int,
        rating: int,
        lat_ref: str,
        lat: float,
        long_ref: str,
        long: float,
        times_shown: int = 0,
    ):
        self.hash_id = hash_id
        self.absolute_path = abs_path
        self.mtime = mtime
        self.orig_date_time = orig_datetime
        self.orientation = orientation
        self.rating = rating
        self.lat_ref = lat_ref
        self.lat = lat
        self.long_ref = long_ref
        self.long = long
        self.times_shown = times_shown

    def get_date_time(self):
        if self.orig_date_time:
            return self.orig_date_time
        else:
            return datetime.fromtimestamp(self.mtime)

    @staticmethod
    def from_picture_file(pic_file: PictureFile):
        pic_data = PictureData(
            pic_file.hash,
            pic_file.path,
            pic_file.mtime,
            pic_file.exif_data.orig_date_time,
            pic_file.exif_data.orientation,
            pic_file.exif_data.rating,
            pic_file.exif_data.lat_ref,
            pic_file.exif_data.lat,
            pic_file.exif_data.long_ref,
            pic_file.exif_data.long,
        )
        return pic_data

    def __repr__(self):
        return str(self.__dict__)


class Metadata:
    key = None

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def __repr__(self):
        return str(self.__dict__)
