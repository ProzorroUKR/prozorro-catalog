import asyncio
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from base64 import urlsafe_b64encode, urlsafe_b64decode
from aiohttp import web
from bson.codec_options import TypeRegistry
from bson.codec_options import CodecOptions
from bson.decimal128 import Decimal128
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.collection import ReturnDocument
from pymongo.errors import PyMongoError, DuplicateKeyError
from catalog.settings import (
    MONGODB_URI, READ_PREFERENCE, WRITE_CONCERN, READ_CONCERN,
    DB_NAME,
    MAX_LIST_LIMIT,
)
from urllib.parse import urlparse, parse_qsl, unquote, urlencode
from catalog.context import get_request, get_request_scheme

logger = logging.getLogger(__name__)

DB = None
session_var = ContextVar('session', default=None)


def get_database():
    return DB


async def init_mongo(*app) -> AsyncIOMotorDatabase:
    global DB

    logger.info('init mongod instance')
    loop = asyncio.get_event_loop()
    conn = AsyncIOMotorClient(MONGODB_URI, io_loop=loop)

    DB = conn.get_database(
        DB_NAME,
        read_preference=READ_PREFERENCE,
        write_concern=WRITE_CONCERN,
        read_concern=READ_CONCERN,
    )
    await asyncio.gather(
        init_category_indexes(),
        init_profile_indexes(),
        init_products_indexes(),
        init_offers_indexes(),
        init_vendor_indexes(),
    )
    return DB


# The stuff below is done to be able store sets (as lists) and decimals (as decimals) types in mongodb bson
# bson.errors.InvalidDocument: cannot encode object: {'ALL_A', 'ALL_B', 'ALL_C'}, of type: <class 'set'>
def fallback_encoder(value):
    if isinstance(value, Decimal):
        return Decimal128(value)
    if isinstance(value, set):
        return list(value)
    return value


type_registry = TypeRegistry(fallback_encoder=fallback_encoder)
codec_options = CodecOptions(type_registry=type_registry)


def get_collection(name):
    return DB.get_collection(name, codec_options=codec_options)


async def cleanup_db_client(app):
    global DB
    if DB is not None:
        DB.client.close()
        DB = None


async def flush_database(*_):
    await asyncio.gather(
        get_category_collection().delete_many({}),
        get_profiles_collection().delete_many({}),
        get_products_collection().delete_many({}),
        get_offers_collection().delete_many({}),
        get_vendor_collection().delete_many({}),
    )


def transaction_generator(func):
    """
    Decorator for async generators
    :param func:
    :return:
    """
    async def decorated(*args, **kwargs):
        async with await DB.client.start_session() as s:
            token = session_var.set(s)
            try:
                async with s.start_transaction():
                    async for result in func(*args, **kwargs):
                        yield result
            finally:
                # without finally
                # in case of exceptions session_var may contain an ended session link
                session_var.reset(token)
    return decorated


@asynccontextmanager
async def transaction_context_manager():
    async with await DB.client.start_session() as s:
        token = session_var.set(s)
        try:
            async with s.start_transaction():
                yield s
        finally:
            # without finally
            # in case of exceptions session_var may contain an ended session link
            session_var.reset(token)


def rename_id(obj):
    if obj:
        obj["id"] = obj.pop("_id")
    return obj


def remove_id(obj):
    if obj:
        obj.pop("_id")
    return obj


async def find_objects(collection, ids):
    filters = {"_id": {"$in": ids}}
    items = await collection.find(
        filters,
    ).to_list(None)
    for i in items:
        rename_id(i)
    return items


async def paginated_result(collection, *_, offset, limit, reverse, filters=None):
    limit = min(limit, MAX_LIST_LIMIT)
    limit = max(limit, 1)
    filters = filters or {}
    if offset:
        if offset and offset[:2] != '20':
            offset = urlsafe_b64decode(offset).decode()
        if offset[:2] != '20' or len(offset) < 20:
            offset = ''
        if reverse:
            filters["dateModified"] = {"$lt": offset}
        else:
            filters["dateModified"] = {"$gt": offset}

    items = await collection.find(
        filters,
        projection={"dateModified": True}
    ).sort(
        [("dateModified",
          DESCENDING if reverse else ASCENDING)]
    ).limit(limit).to_list(None)
    result = {"data": [rename_id(i) for i in items]}

    # generate forward & back links
    request = get_request()
    req_scheme = get_request_scheme()
    base_url = f"{req_scheme}://{request.host}"

    # next page
    next_params = {
        "offset": offset,
        "limit": limit,
    }
    prev_params = dict(next_params)
    if items:
        next_params["offset"] = items[-1]['dateModified']
        prev_params["offset"] = items[0]['dateModified']
    if reverse:
        next_params["descending"] = "1"
    next_path = f"{request.path}?{urlencode(next_params)}"
    result["next_page"] = {
        "offset": next_params["offset"],
        "path": next_path,
        "uri": f"{base_url}{next_path}"
    }

    # prev page
    if offset:
        if not reverse:
            prev_params["descending"] = "1"
        prev_path = f"{request.path}?{urlencode(prev_params)}"
        result["prev_page"] = {
            "offset": prev_params["offset"],
            "path": prev_path,
            "uri": f"{base_url}{prev_path}"
        }
    return result


def get_sequences_collection():
    return get_collection("sequences")


async def get_next_sequence_value(uid):
    collection = get_sequences_collection()
    result = await collection.find_one_and_update(
        {'_id': uid},
        {"$inc": {"value": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    return result["value"]


async def insert_object(collection, data):
    document = dict(**data)
    document["_id"] = document.pop("id")
    try:
        result = await collection.insert_one(document)
    except DuplicateKeyError:
        raise web.HTTPBadRequest(text=f"Document with id {document['_id']} already exists")
    return result.inserted_id


async def update_object(collection, data):
    document = dict(**data)
    document["_id"] = uid = document.pop("id")
    await collection.find_one_and_replace(
        {'_id': uid},
        document,
        session=session_var.get(),
    )


# category
def get_category_collection():
    return get_collection("category")


async def init_category_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    try:
        await get_category_collection().create_indexes(
            [modified_index]
        )
    except PyMongoError as e:
        logger.exception(e)


async def find_categories(**kwargs):
    collection = get_category_collection()
    result = await paginated_result(
        collection, **kwargs
    )
    return result


async def read_category(category_id, projection=None):
    projection = projection or {}
    category = await get_category_collection().find_one(
        {'_id': category_id},
        projection=projection,
        session=session_var.get(),
    )
    if not category:
        raise web.HTTPNotFound(text="Category not found")
    return rename_id(category)


async def insert_category(data):
    inserted_id = await insert_object(get_category_collection(), data)
    return inserted_id


async def update_category(category):
    await update_object(get_category_collection(), category)


@asynccontextmanager
async def read_and_update_category(uid):
    data = await read_category(uid)
    yield data
    await update_category(data)


# profiles
def get_profiles_collection():
    return get_collection("profiles")


async def init_profile_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    try:
        await get_profiles_collection().create_indexes(
            [modified_index]
        )
    except PyMongoError as e:
        logger.exception(e)


async def insert_profile(data):
    inserted_id = await insert_object(
        get_profiles_collection(),
        data
    )
    return inserted_id


async def find_profiles(**kwargs):
    collection = get_profiles_collection()
    result = await paginated_result(
        collection, **kwargs
    )
    return result


async def read_profile(profile_id):
    profile = await get_profiles_collection().find_one(
        {'_id': profile_id},
        session=session_var.get(),
    )
    if not profile:
        raise web.HTTPNotFound(text="Profile not found")
    return rename_id(profile)


async def update_profile(profile):
    await update_object(get_profiles_collection(), profile)


@asynccontextmanager
async def read_and_update_profile(profile_id):
    profile = await read_profile(profile_id)
    yield profile
    await update_profile(profile)


# criteria

def get_collection_by_obj_name(obj_name):
    collection_by_obj_name = {
        "profile": get_profiles_collection,
        "category": get_category_collection,
    }

    collection = collection_by_obj_name[obj_name]
    return collection()


async def read_obj_criteria(obj_name, obj_id):
    collection = get_collection_by_obj_name(obj_name)

    profile_criteria = await collection.find_one(
        {"_id": obj_id},
        {"criteria": 1, "access": 1},
        session=session_var.get()
    )
    if not profile_criteria:
        raise web.HTTPNotFound(text=f"{obj_name} not found")
    return remove_id(profile_criteria)


async def read_obj_criterion(obj_name, obj_id, criterion_id):
    collection = get_collection_by_obj_name(obj_name)
    async for profile_criterion in collection.aggregate(
        [
            {"$match": {"_id": obj_id}},
            {"$unwind": "$criteria"},
            {"$match": {"criteria.id": criterion_id}},
            {"$project": {"criteria": 1, "access": 1, "dateModified": 1}}
        ],
        session=session_var.get()
    ):
        if not profile_criterion["criteria"]:
            raise web.HTTPNotFound(text="Criteria not found")
        return remove_id(profile_criterion)
    raise web.HTTPNotFound(text="Criteria not found")


async def update_obj_criterion(obj_name, obj_id, data, criterion_id, dateModified):
    collection = get_collection_by_obj_name(obj_name)
    update_data = {"dateModified": dateModified}
    for k, v in data.items():
        update_data[f"criteria.$.{k}"] = v
    await collection.update_one(
        {'_id': obj_id, "criteria.id": criterion_id},
        {"$set": update_data},
        session=session_var.get(),
    )


@asynccontextmanager
async def read_and_update_obj_criterion(obj_name, obj_id, criterion_id):
    profile = await read_obj_criterion(obj_name, obj_id, criterion_id)
    yield profile
    await update_obj_criterion(obj_name, obj_id, profile["criteria"], criterion_id, profile["dateModified"])


async def delete_obj_criterion(obj_name, obj_id, criterion_id, dateModified):
    collection = get_collection_by_obj_name(obj_name)
    updated = await collection.update_one(
        {'_id': obj_id, "criteria.id": criterion_id},
        {
            "$pull": {"criteria": {"id": criterion_id}},
            "$set": {"dateModified": dateModified}
        },
        session=session_var.get(),
    )
    if updated.modified_count == 0:
        raise web.HTTPNotFound(text="Criterion not found")


async def delete_obj_criterion_rg(obj_name, obj_id, criterion_id, dateModified):
    collection = get_collection_by_obj_name(obj_name)
    updated = await collection.update_one(
        {'_id': obj_id, "criteria.id": criterion_id},
        {
            "$pull": {"criteria": {"id": criterion_id}},
            "$set": {"dateModified": dateModified}
        },
        session=session_var.get(),
    )
    if updated.modified_count == 0:
        raise web.HTTPNotFound(text="Criterion not found")


async def get_access_token(obj_name, obj_id):
    collection = get_collection_by_obj_name(obj_name)
    profile = await collection.find_one(
        {"_id": obj_id},
        {"access": 1},
        session=session_var.get()
    )
    if not profile:
        raise web.HTTPNotFound(text=f"{obj_name} not found")
    return remove_id(profile)


# products
def get_products_collection():
    return get_collection("products")


async def init_products_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    try:
        await get_products_collection().create_indexes(
            [modified_index]
        )
    except PyMongoError as e:
        logger.exception(e)


async def insert_product(data):
    inserted_id = await insert_object(
        get_products_collection(),
        data
    )
    return inserted_id


async def find_products(**kwargs):
    collection = get_products_collection()
    result = await paginated_result(
        collection, **kwargs
    )
    return result


async def read_product(uid, filters=None):
    if filters is None:
        filters = {}
    data = await get_products_collection().find_one(
        {'_id': uid, **filters},
        session=session_var.get(),
    )
    if not data:
        raise web.HTTPNotFound(text="Product not found")
    return rename_id(data)


async def update_product(obj):
    await update_object(get_products_collection(), obj)


@asynccontextmanager
async def read_and_update_product(uid, filters=None):
    obj = await read_product(uid, filters)
    yield obj
    await update_product(obj)


# offers
def get_offers_collection():
    return get_collection("offers")


async def init_offers_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    try:
        await get_offers_collection().create_indexes(
            [modified_index]
        )
    except PyMongoError as e:
        logger.exception(e)


async def insert_offer(data):
    inserted_id = await insert_object(
        get_offers_collection(),
        data
    )
    return inserted_id


async def find_offers(**kwargs):
    collection = get_offers_collection()
    result = await paginated_result(
        collection, **kwargs
    )
    return result


async def read_offer(uid):
    data = await get_offers_collection().find_one(
        {'_id': uid},
        session=session_var.get(),
    )
    if not data:
        raise web.HTTPNotFound(text="Product not found")
    return rename_id(data)


async def update_offer(obj):
    await update_object(get_offers_collection(), obj)


@asynccontextmanager
async def read_and_update_offer(uid):
    obj = await read_offer(uid)
    yield obj
    await update_offer(obj)


# vendor
def get_vendor_collection():
    return get_collection("vendors")


async def init_vendor_indexes():
    modified_index = IndexModel(
        [("dateModified", ASCENDING)],
        partialFilterExpression={"isActivated": True},
        background=True,
        name="activated_vendors"
    )
    try:
        await get_vendor_collection().create_indexes([modified_index])
    except PyMongoError as e:
        logger.exception(e)


async def find_vendors(**kwargs):
    collection = get_vendor_collection()
    result = await paginated_result(
        collection, **kwargs
    )
    return result


async def read_vendor(uid):
    object = await get_vendor_collection().find_one(
        {'_id': uid},
        session=session_var.get(),
    )
    if not object:
        raise web.HTTPNotFound(text="Vendor not found")
    return rename_id(object)


async def insert_vendor(data):
    inserted_id = await insert_object(get_vendor_collection(), data)
    return inserted_id


async def update_vendor(data):
    await update_object(get_vendor_collection(), data)


@asynccontextmanager
async def read_and_update_vendor(uid):
    data = await read_vendor(uid)
    yield data
    await update_vendor(data)
