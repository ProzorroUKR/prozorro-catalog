from pymongo import ReadPreference
from pymongo.write_concern import WriteConcern
from pymongo.read_concern import ReadConcern
from zoneinfo import ZoneInfo
import configparser
import logging
import sys
import os

logger = logging.getLogger(__name__)

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://mongo:27017/")
DB_NAME = os.environ.get("DB_NAME", "catalog")
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

# directory to store images
IMG_DIR = os.getenv('IMG_DIR', '/app/images')
if not os.path.exists(IMG_DIR):
    logger.warning(f"IMG_DIR '{IMG_DIR}' does not exist. Created")
    os.makedirs(IMG_DIR)
IMG_PATH = os.getenv('IMG_PATH', '/static/images')

ALLOWED_IMG_TYPES = os.getenv('ALLOWED_IMG_TYPES', 'jpeg,png').split(",")

IMG_STORE_DIR_NAME_LEN = int(os.getenv('IMG_STORE_DIR_NAME_LEN', 2))
IMG_STORE_DIR_LEVELS = int(os.getenv('IMG_STORE_DIR_LEVELS', 3))
assert IMG_STORE_DIR_LEVELS * IMG_STORE_DIR_NAME_LEN < 32, "We only use 32 long uuid4 for both path and name"
