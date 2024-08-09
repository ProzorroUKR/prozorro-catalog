from aiohttp_client_cache.backends.mongodb import MongoDBBackend
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReadPreference
from pymongo.write_concern import WriteConcern
from pymongo.read_concern import ReadConcern
from zoneinfo import ZoneInfo
from uuid import uuid4
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
CLIENT_MAX_SIZE = int(os.getenv('CLIENT_MAX_SIZE', 1024 ** 2 * 100))


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
IMG_SIZE_LIMIT = os.getenv('IMG_SIZE_LIMIT', 1000000)  # default limit 1 Mb

IMG_STORE_DIR_NAME_LEN = int(os.getenv('IMG_STORE_DIR_NAME_LEN', 2))
IMG_STORE_DIR_LEVELS = int(os.getenv('IMG_STORE_DIR_LEVELS', 3))
assert IMG_STORE_DIR_LEVELS * IMG_STORE_DIR_NAME_LEN < 32, "We only use 32 long uuid4 for both path and name"

CATALOG_DATA = os.getenv("CATALOG_DATA")

OPENPROCUREMENT_API_URL = os.environ.get("OPENPROCUREMENT_API_URL", "http://api.master.k8s.prozorro.gov.ua/api/2.5")


DOC_SERVICE_URL = os.environ.get("DOC_SERVICE_URL", "https://docs.prozorro.gov.ua")
DOC_SERVICE_DEP_URL = os.environ.get("DOC_SERVICE_DEP_URL", "")

# to check document urls are really from the doc service
# when they come to this api
# can be taken from doc service config
DOC_SERVICE_SEEDS = [v.encode() for v in os.environ.get("DOC_SERVICE_SEEDS", uuid4().hex * 2).split(",")]

# there're can be many seeds to rotate them
# so part of it is sent as `&Key=` in url
# this param can configure length, however I don't think we gonna change this
DOC_SERVICE_KEY_LENGTH = int(os.environ.get("DOC_SERVICE_KEY_LENGTH", 8))

# to make a signature
# so when we redirect ot doc service
# it knows we come from this api
# should be generated and put both here and to the doc service config
DOC_SERVICE_SIGNING_SEED = os.environ.get("DOC_SERVICE_SIGNING_SEED", uuid4().hex * 2).encode()

MEDICINE_API_URL = os.environ.get("MEDICINE_API_URL", "https://medicines-registry.prozorro.gov.ua/api/1.0")
MEDICINE_SCHEMES = ("INN", "ATC")

# cache settings
EXPIRE_CACHE_AFTER = int(os.environ.get("EXPIRE_CACHE_AFTER", 3600))  # value in seconds, default 1 hour
CACHE_BACKEND = MongoDBBackend(
    connection=AsyncIOMotorClient(MONGODB_URI),
    cache_name=DB_NAME,
    expire_after=EXPIRE_CACHE_AFTER,
)


CPB_USERNAME = "cpb"

# hashed value of 321e8b0b4fc725c525d38de6e458965f
CPB_TOKEN = os.environ.get("CPB_TOKEN", "2a22eebe494e290141febee51004984d2d4a0a539bc1a5e8732d07104e337e84")
