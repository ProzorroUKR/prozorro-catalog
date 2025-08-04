import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from aiohttp import web
from bson.codec_options import TypeRegistry
from bson.codec_options import CodecOptions
from bson.decimal128 import Decimal128
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel, ReadPreference
from pymongo.collection import ReturnDocument
from pymongo.errors import PyMongoError, DuplicateKeyError
from catalog.settings import (
    MONGODB_URI, READ_PREFERENCE, WRITE_CONCERN, READ_CONCERN,
    DB_NAME,
    MAX_LIST_LIMIT,
)
from urllib.parse import urlencode
from catalog.context import get_request, get_request_scheme, get_db_session, session_var
from catalog.utils import get_next_rev

logger = logging.getLogger(__name__)

DB = None


def get_database():
    return DB


async def init_mongo(*app) -> AsyncIOMotorDatabase:
    global DB

    logger.info('init mongodb instance')
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
        init_contributor_indexes(),
        init_request_indexes(),
        init_tag_indexes(),
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


def get_collection(name, read_preference=None):
    collection = DB.get_collection(name, codec_options=codec_options)
    if read_preference:
        collection = collection.with_options(read_preference=read_preference)
    return collection


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
        get_contributor_collection().delete_many({}),
        get_product_request_collection().delete_many({}),
        get_tag_collection().delete_many({}),
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
    if obj and "_id" in obj:
        obj["id"] = obj.pop("_id")
        if obj.get("_rev"):  # if it is empty, just skip (e.g. not to mention rev for paginated results)
            obj["rev"] = obj.pop("_rev")
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


async def paginated_result(collection, *_, offset, limit, reverse, filters=None, opt_fields=None):
    limit = min(limit, MAX_LIST_LIMIT)
    limit = max(limit, 1)
    filters = filters or {}
    if offset:
        try:
            datetime.fromisoformat(offset.replace(" ", "+"))
        except Exception:
            raise web.HTTPBadRequest(text=f"Invalid offset: {offset}")
        if reverse:
            filters["dateModified"] = {"$lt": offset}
        else:
            filters["dateModified"] = {"$gt": offset}

    projection = {"dateModified": True}
    if opt_fields is not None:
        for field in opt_fields:
            projection[field] = True

    items = await collection.find(
        filters,
        projection=projection,
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
    document["_rev"] = get_next_rev()
    try:
        result = await collection.insert_one(document)
    except DuplicateKeyError as e:
        detail = e.details
        if detail and "keyValue" in detail:
            duplicated_field = list(detail["keyValue"].keys())[0]
            duplicated_value = detail["keyValue"][duplicated_field]
            raise web.HTTPBadRequest(
                text=f"Duplicate value for '{duplicated_field}': '{duplicated_value}'"
            )
        raise web.HTTPBadRequest(text=f"Document with id {document['_id']} already exists")
    return result.inserted_id


async def update_object(collection, data):
    revision = data.pop("rev" if "rev" in data else "_rev", None)
    document = dict(**data)
    document["_id"] = uid = document.pop("id")
    document["_rev"] = get_next_rev(revision)
    match_dict = {'_id': uid}
    # add revisions filter in match dict for object which already has this functionality
    if revision is not None:
        match_dict["_rev"] = revision
    result = await collection.find_one_and_replace(
        match_dict,
        document,
        session=get_db_session(),
    )
    if result is None:
        raise web.HTTPConflict(text="Conflict while writing document. Please, retry.")


# category
def get_category_collection(read_preference=None):
    return get_collection("category", read_preference=read_preference)


async def init_category_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    tags_index = IndexModel([("tags", ASCENDING)], background=True)
    try:
        await get_category_collection().create_indexes(
            [modified_index, tags_index]
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
        session=get_db_session(),
    )
    if not category:
        raise web.HTTPNotFound(text="Category not found")
    return rename_id(category)


async def insert_category(data):
    inserted_id = await insert_object(get_category_collection(), data)
    return inserted_id


async def update_category(category):
    await update_object(get_category_collection(read_preference=ReadPreference.PRIMARY), category)


@asynccontextmanager
async def read_and_update_category(uid):
    data = await read_category(uid)
    yield data
    await update_category(data)


# profiles
def get_profiles_collection(read_preference=None):
    return get_collection("profiles", read_preference=read_preference)


async def init_profile_indexes():
    # db.contributors.createIndex({ "dateModified": 1 })
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    tags_index = IndexModel([("tags", ASCENDING)], background=True)
    try:
        await get_profiles_collection().create_indexes(
            [modified_index, tags_index]
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
        session=get_db_session(),
    )
    if not profile:
        raise web.HTTPNotFound(text="Profile not found")
    return rename_id(profile)


async def update_profile(profile):
    await update_object(get_profiles_collection(read_preference=ReadPreference.PRIMARY), profile)


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
        session=get_db_session()
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
        ],
        session=get_db_session()
    ):
        if not profile_criterion["criteria"]:
            raise web.HTTPNotFound(text="Criteria not found")
        return remove_id(profile_criterion)
    raise web.HTTPNotFound(text="Criteria not found")


async def delete_obj_criterion(obj_name, obj_id, criterion_id, dateModified):
    collection = get_collection_by_obj_name(obj_name)
    updated = await collection.update_one(
        {'_id': obj_id, "criteria.id": criterion_id},
        {
            "$pull": {"criteria": {"id": criterion_id}},
            "$set": {"dateModified": dateModified}
        },
        session=get_db_session(),
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
        session=get_db_session(),
    )
    if updated.modified_count == 0:
        raise web.HTTPNotFound(text="Criterion not found")


async def get_access_token(obj_name, obj_id):
    collection = get_collection_by_obj_name(obj_name)
    profile = await collection.find_one(
        {"_id": obj_id},
        {"access": 1},
        session=get_db_session()
    )
    if not profile:
        raise web.HTTPNotFound(text=f"{obj_name} not found")
    return remove_id(profile)


# products
def get_products_collection(read_preference=None):
    return get_collection("products", read_preference=read_preference)


async def init_products_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    # for quicker migration
    # TODO: delete after migration
    category_index = IndexModel([("relatedCategory", ASCENDING)], background=True)
    profile_index = IndexModel([("relatedProfiles", ASCENDING)], background=True)
    try:
        await get_products_collection().create_indexes(
            [modified_index, category_index, profile_index]
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
        session=get_db_session(),
    )
    if not data:
        raise web.HTTPNotFound(text="Product not found")
    return rename_id(data)


async def update_product(obj):
    await update_object(get_products_collection(read_preference=ReadPreference.PRIMARY), obj)


@asynccontextmanager
async def read_and_update_product(uid, filters=None):
    obj = await read_product(uid, filters)
    yield obj
    await update_product(obj)


# offers
def get_offers_collection(read_preference=None):
    return get_collection("offers", read_preference=read_preference)


async def init_offers_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    category_index = IndexModel([("relatedCategory", ASCENDING)], background=True)
    try:
        await get_offers_collection().create_indexes(
            [modified_index, category_index]
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
        session=get_db_session(),
    )
    if not data:
        raise web.HTTPNotFound(text="Product not found")
    return rename_id(data)


async def update_offer(obj):
    await update_object(get_offers_collection(read_preference=ReadPreference.PRIMARY), obj)


@asynccontextmanager
async def read_and_update_offer(uid):
    obj = await read_offer(uid)
    yield obj
    await update_offer(obj)


# vendor
def get_vendor_collection(read_preference=None):
    return get_collection("vendors", read_preference=read_preference)


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
        session=get_db_session(),
    )
    if not object:
        raise web.HTTPNotFound(text="Vendor not found")
    return rename_id(object)


async def insert_vendor(data):
    inserted_id = await insert_object(get_vendor_collection(), data)
    return inserted_id


async def update_vendor(data):
    await update_object(get_vendor_collection(read_preference=ReadPreference.PRIMARY), data)


@asynccontextmanager
async def read_and_update_vendor(uid):
    data = await read_vendor(uid)
    yield data
    await update_vendor(data)


# contributor
def get_contributor_collection(read_preference=None):
    return get_collection("contributors", read_preference=read_preference)


async def init_contributor_indexes():
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    try:
        await get_contributor_collection().create_indexes([modified_index])
    except PyMongoError as e:
        logger.exception(e)


async def find_contributors(**kwargs):
    collection = get_contributor_collection()
    result = await paginated_result(
        collection, **kwargs,
    )
    return result


async def read_contributor(uid):
    contributor = await get_contributor_collection().find_one(
        {'_id': uid},
        session=get_db_session(),
    )
    if not contributor:
        raise web.HTTPNotFound(text="Contributor not found")
    return rename_id(contributor)


async def insert_contributor(data):
    inserted_id = await insert_object(get_contributor_collection(), data)
    return inserted_id


async def update_contributor(data):
    await update_object(get_contributor_collection(read_preference=ReadPreference.PRIMARY), data)


@asynccontextmanager
async def read_and_update_contributor(uid):
    data = await read_contributor(uid)
    yield data
    await update_contributor(data)


# product requests
def get_product_request_collection(read_preference=None):
    return get_collection("requests", read_preference=read_preference)


async def init_request_indexes():
    # db.requests.createIndex({ "dateModified": 1 })
    modified_index = IndexModel([("dateModified", ASCENDING)], background=True)
    try:
        await get_product_request_collection().create_indexes([modified_index])
    except PyMongoError as e:
        logger.exception(e)


async def find_product_requests(**kwargs):
    collection = get_product_request_collection()
    result = await paginated_result(
        collection, **kwargs,
    )
    return result


async def read_product_request(uid):
    contributor = await get_product_request_collection().find_one(
        {'_id': uid},
        session=get_db_session(),
    )
    if not contributor:
        raise web.HTTPNotFound(text="Request not found")
    return rename_id(contributor)


async def insert_product_request(data):
    inserted_id = await insert_object(get_product_request_collection(), data)
    return inserted_id


async def update_product_request(data):
    await update_object(get_product_request_collection(read_preference=ReadPreference.PRIMARY), data)


@asynccontextmanager
async def read_and_update_product_request(uid):
    data = await read_product_request(uid)
    yield data
    await update_product_request(data)


# tags
def get_tag_collection(read_preference=None):
    return get_collection("tag", read_preference=read_preference)


async def init_tag_indexes():
    code_index = IndexModel([("code", ASCENDING)], background=True, unique=True)
    name_index = IndexModel([("name", ASCENDING)], background=True, unique=True)
    name_en_index = IndexModel([("name_en", ASCENDING)], background=True, unique=True)
    try:
        await get_tag_collection().create_indexes([code_index, name_index, name_en_index])
    except PyMongoError as e:
        logger.exception(e)


async def find_tags(limit, active):
    collection = get_tag_collection()
    limit = min(limit, MAX_LIST_LIMIT)
    limit = max(limit, 1)
    filters = {}
    items = await collection.find(filters).limit(limit).to_list(None)
    items = [rename_id(i) for i in items]
    return items


async def read_tag(tag_id):
    tag = await get_tag_collection().find_one(
        {'code': tag_id},
        session=get_db_session(),
    )
    if not tag:
        raise web.HTTPNotFound(text="Tag not found")
    return rename_id(tag)


async def insert_tag(data):
    inserted_id = await insert_object(get_tag_collection(), data)
    return inserted_id


async def update_tag(tag):
    await update_object(get_tag_collection(read_preference=ReadPreference.PRIMARY), tag)


@asynccontextmanager
async def read_and_update_tag(uid):
    data = await read_tag(uid)
    yield data
    try:
        await update_tag(data)
    except DuplicateKeyError as e:
        detail = e.details
        if detail and "keyValue" in detail:
            duplicated_field = list(detail["keyValue"].keys())[0]
            duplicated_value = detail["keyValue"][duplicated_field]
            raise web.HTTPBadRequest(
                text=f"Duplicate value for '{duplicated_field}': '{duplicated_value}'"
            )
        raise web.HTTPBadRequest(text=f"Document with id {data['_id']} already exists")


async def delete_tag(tag_id):
    result = await get_tag_collection().delete_one(
        {'code': tag_id},
        session=get_db_session(),
    )
    if result.deleted_count == 0:
        raise web.HTTPNotFound(text="Tag not found")


async def find_objects_with_tag(tag_id):
    """
    Find categories and profiles with particular tag.
    Limit by 10 results just for mentioning list of objects in exception.
    """
    category_ids = await get_category_collection().find(
        {'tags': tag_id},
        session=get_db_session(),
    ).limit(10).distinct("_id")
    if category_ids:
        raise web.HTTPBadRequest(text=f"Tag `{tag_id}` is used in categories {category_ids}")
    profile_ids = await get_profiles_collection().find(
        {'tags': tag_id},
        session=get_db_session(),
    ).limit(10).distinct("_id")
    if profile_ids:
        raise web.HTTPBadRequest(text=f"Tag `{tag_id}` is used in profiles {profile_ids}")


async def validate_tags_exist(tag_codes: list[str]) -> None:
    cursor = get_tag_collection().find(
        {"code": {"$in": tag_codes}},
        {"code": 1, "_id": 0},
        session=get_db_session()
    )
    existing_tags = [doc["code"] async for doc in cursor]

    missing = set(tag_codes) - set(existing_tags)
    if missing:
        raise web.HTTPBadRequest(text=f"Tags not found: {', '.join(missing)}")


async def wait_until_cluster_time_reached(session, target_cluster_time, timeout=5.0):
    """
    Waits until the session's cluster_time reaches or exceeds the target_cluster_time.
    """
    start_time = time.time()
    while True:
        await session.client.admin.command("ping", session=session)
        current_cluster_time = session.cluster_time

        if current_cluster_time and current_cluster_time["clusterTime"] >= target_cluster_time["clusterTime"]:
            break

        if time.time() - start_time > timeout:
            raise TimeoutError("Timed out waiting for clusterTime to reach target.")

        await asyncio.sleep(0.1)
