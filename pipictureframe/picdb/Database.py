import logging
from datetime import datetime

import sqlalchemy
from sqlalchemy import Column, String, Integer, DateTime, Float
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.exc import UnmappedClassError

from pipictureframe.picdb.DbObjects import PictureData, Metadata

log = logging.getLogger(__name__)


VERSION_STRING = "version"
CURRENT_DB_VERSION = 1
LAST_DB_UPDATE_KEY_STR = "last_db_update"
LAST_DB_UPDATE_FMT_STR = "%Y-%m-%d %H:%M:%S"


class Database:
    def __init__(self, connection_string: str, echo=False):
        self.engine = sqlalchemy.create_engine(connection_string, echo=echo)
        self.connection = self.engine.connect()
        self.alchemy_metadata = sqlalchemy.MetaData(bind=self.engine)
        self.sm = sessionmaker()
        self._initialize_db_picture_mapping()
        self._initizalize_metadata_table()
        self.alchemy_metadata.create_all()
        self.create_inital_metadata_objects()
        self.version = self._get_db_version()

    def create_inital_metadata_objects(self):
        try:
            session = self.get_session()
            session.add(Metadata(VERSION_STRING, str(CURRENT_DB_VERSION)))
            session.add(
                Metadata(
                    LAST_DB_UPDATE_KEY_STR,
                    datetime.now().strftime(LAST_DB_UPDATE_FMT_STR),
                )
            )
            session.commit()
            log.debug("Setting up initial metadata objects successful.")
        except IntegrityError:
            log.debug("Metadata objects already set up. Probably already existing db.")
            pass
        finally:
            session.close()

    def _get_db_version(self):
        session = self.get_session()
        version_obj: Metadata = (
            session.query(Metadata).filter(Metadata.key == VERSION_STRING).one()
        )
        version = version_obj.value
        session.close()
        log.debug(f"Retrieved db version = {version}")
        return int(version)

    def _initialize_db_picture_mapping(self):
        try:
            sqlalchemy.orm.class_mapper(PictureData)
        except UnmappedClassError:  # map class as it is not yet mapped.
            pic_data_map = sqlalchemy.Table(
                "pictures",
                self.alchemy_metadata,
                Column("hash_id", String(50), primary_key=True),
                Column("absolute_path", String(256)),
                Column("mtime", Integer),
                Column("orig_date_time", DateTime),
                Column("orientation", Integer),
                Column("rating", Integer),
                Column("lat_ref", String(1)),
                Column("lat", Float),
                Column("long_ref", String(1)),
                Column("long", Float),
                Column("times_shown", Integer),
            )
            sqlalchemy.orm.mapper(PictureData, pic_data_map)

    def _initizalize_metadata_table(self):
        try:
            sqlalchemy.orm.class_mapper(Metadata)
        except UnmappedClassError:
            metadata_map = sqlalchemy.Table(
                "metadata",
                self.alchemy_metadata,
                Column("key", String(256), primary_key=True),
                Column("value", String(1024)),
            )
            sqlalchemy.orm.mapper(Metadata, metadata_map)

    def get_session(self) -> Session:
        return self.sm()

    def close(self):
        self.sm.close_all()
        self.connection.close()
