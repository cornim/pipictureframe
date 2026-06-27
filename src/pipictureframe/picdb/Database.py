import logging
from datetime import datetime

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

from pipictureframe.picdb.DbObjects import Base, Metadata

log = logging.getLogger(__name__)


VERSION_STRING = "version"
CURRENT_DB_VERSION = 2
LAST_DB_UPDATE_KEY_STR = "last_db_update"
LAST_DB_UPDATE_FMT_STR = "%Y-%m-%d %H:%M:%S.%f"


class Database:
    def __init__(self, connection_string: str, echo=False, expire_on_commit=True):
        self.engine = sqlalchemy.create_engine(connection_string, echo=echo)
        self._configure_sqlite_pragmas()
        # Keep one connection open for the lifetime of this object so that an
        # in-memory SQLite database (which only exists for as long as its
        # connection does) is not discarded between sessions.
        self.connection = self.engine.connect()
        self.sm = sessionmaker(bind=self.engine, expire_on_commit=expire_on_commit)
        # The ORM mapping lives on the declarative Base in DbObjects, so the
        # schema is simply created on this engine.
        Base.metadata.create_all(self.engine)
        self._create_initial_metadata_objects()
        self.version = self._get_db_version()

    def _configure_sqlite_pragmas(self):
        """Improve concurrent access for SQLite databases.

        SQLite serializes writers and, by default, raises "database is locked"
        immediately when a connection cannot acquire the write lock. Because the
        application accesses the database from both the main process and a
        background update process, this leads to spurious failures.

        Enabling WAL (write-ahead logging) lets readers and a single writer work
        concurrently, and a busy timeout makes a connection wait for the lock to
        be released instead of failing right away. These pragmas are only
        relevant for SQLite, so other backends are left untouched.
        """
        if self.engine.dialect.name != "sqlite":
            return

        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # WAL is persisted in the database file; busy_timeout is per
            # connection and therefore has to be set on every new connection.
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    def _create_initial_metadata_objects(self):
        session = self.get_session()
        try:
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

    def get_session(self) -> Session:
        return self.sm()

    def set_last_update_time(self, update_time: datetime, session: Session = None):
        generate_session = False if session else True
        if generate_session:
            session = self.get_session()

        update_obj = Metadata(
            LAST_DB_UPDATE_KEY_STR, datetime.now().strftime(LAST_DB_UPDATE_FMT_STR)
        )
        session.merge(update_obj)

        if generate_session:
            session.commit()
            session.close()

    def get_last_update_time(self, session: Session = None) -> datetime:
        generate_session = False if session else True
        if generate_session:
            session = self.get_session()
        last_db_update = datetime.strptime(
            session.query(Metadata)
            .filter(Metadata.key == LAST_DB_UPDATE_KEY_STR)
            .one()
            .value,
            LAST_DB_UPDATE_FMT_STR,
        )
        if generate_session:
            session.commit()
            session.close()
        return last_db_update

    def close(self):
        sqlalchemy.orm.session.close_all_sessions()
        self.connection.close()
        self.engine.dispose()
