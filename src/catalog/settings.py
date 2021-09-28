from pymongo import ReadPreference
from pymongo.write_concern import WriteConcern
from pymongo.read_concern import ReadConcern
from zoneinfo import ZoneInfo
import configparser
import sys
import os

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://mongo:27017/")
ENGINE_DB_NAME = os.environ.get("ENGINE_DB_NAME", "risk_engine")
# 'PRIMARY', 'PRIMARY_PREFERRED', 'SECONDARY', 'SECONDARY_PREFERRED', 'NEAREST',
READ_PREFERENCE = getattr(ReadPreference, os.environ.get("READ_PREFERENCE", "PRIMARY"))
raw_write_concert = os.environ.get("WRITE_CONCERN", "1")
WRITE_CONCERN = WriteConcern(w=int(raw_write_concert) if raw_write_concert.isnumeric() else raw_write_concert)
READ_CONCERN = ReadConcern(level=os.environ.get("READ_CONCERN") or None)

SWAGGER_DOC_AVAILABLE = bool(os.environ.get("SWAGGER_DOC_AVAILABLE", True))
MAX_LIST_LIMIT = int(os.environ.get("MAX_LIST_LIMIT", 10000))

IS_TEST = "test" in sys.argv[0]
SENTRY_DSN = os.getenv('SENTRY_DSN')
TIMEZONE = ZoneInfo('Europe/Kiev')


AUTH_PATH = os.getenv('AUTH_PATH', '/app/auth.ini')
config = configparser.ConfigParser(allow_no_value=True)
config.read(AUTH_PATH)
AUTH_DATA = {section_name: {name: secret
                            for name, secret in section.items()}
             for section_name, section in config.items()}
# {'DEFAULT': [],
#  'category': [('test.prozorro.ua', None), ..],
#  'profile': [('test.prozorro.ua', None), ...
