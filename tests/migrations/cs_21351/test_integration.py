from copy import deepcopy
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from catalog.migrations.cs_21351_set_localization_tag import (
    TAG_DATA,
    get_or_create_localization_tag,
    migrate_collection_tags,
)
from tests.utils import get_fixture_json


@pytest.fixture
async def tags_collection(db):
    yield db.get_collection("tag")


async def test_get_existing_tag(tags_collection):
    _id = uuid4().hex
    await tags_collection.insert_one({**TAG_DATA, "_id": _id})
    assert await get_or_create_localization_tag() == TAG_DATA["code"]
    assert await tags_collection.count_documents({"code": TAG_DATA["code"]}) == 1
    tag = await tags_collection.find_one({"code": TAG_DATA["code"]})
    assert tag["_id"] == _id


async def test_create_new_tag(tags_collection):
    await tags_collection.delete_many({})
    with patch("catalog.migrations.cs_21351_set_localization_tag.uuid4", return_value=Mock(hex="test_hex")):
        assert await get_or_create_localization_tag() == TAG_DATA["code"]
    assert await tags_collection.count_documents({"code": TAG_DATA["code"]}) == 1
    tag = await tags_collection.find_one({"code": TAG_DATA["code"]})
    assert tag["_id"] == "test_hex"


@pytest.mark.parametrize(
    ("collection_name", "fixture_name"),
    [
        pytest.param("category", "category"),
        pytest.param("profiles", "profile"),
    ],
)
@pytest.mark.parametrize(
    ("create_data", "check_object"),
    [
        # no tags existed, tag added
        pytest.param(
            lambda data: (
                data.update(
                    {
                        "_id": uuid4().hex,
                        "dateModified": "2025-01-01T00:00:00+02:00",
                        "criteria": [
                            {"classification": {"id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"}},
                            {"classification": {"id": "another criterion id"}},
                        ],
                    }
                ),
                data.pop("tags", None),
            ),
            lambda data, doc: (
                data.get("dateModified") != doc.get("dateModified"),
                data.get("tags", []) == [TAG_DATA["code"]],
            ),
        ),
        # tag added
        pytest.param(
            lambda data: (
                data.update(
                    {
                        "_id": uuid4().hex,
                        "dateModified": "2025-01-01T00:00:00+02:00",
                        "criteria": [
                            {"classification": {"id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"}},
                        ],
                        "tags": [],
                    }
                ),
            ),
            lambda data, doc: (
                data.get("dateModified") != doc.get("dateModified"),
                data.get("tags", []) == [TAG_DATA["code"]],
            ),
        ),
        # tag existed
        pytest.param(
            lambda data: (
                data.update(
                    {
                        "_id": uuid4().hex,
                        "dateModified": "2025-01-01T00:00:00+02:00",
                        "criteria": [
                            {"classification": {"id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"}},
                        ],
                        "tags": [TAG_DATA["code"]],
                    }
                ),
            ),
            lambda data, doc: (
                data.get("dateModified") == doc.get("dateModified"),
                data.get("tags", []) == [TAG_DATA["code"]],
            ),
        ),
        # tag not added
        pytest.param(
            lambda data: (
                data.update(
                    {
                        "_id": uuid4().hex,
                        "dateModified": "2025-01-01T00:00:00+02:00",
                        "criteria": [
                            {"classification": {"id": "another criterion id"}},
                        ],
                        "tags": [],
                    }
                ),
            ),
            lambda data, doc: (
                data.get("dateModified") == doc.get("dateModified"),
                data.get("tags", []) == [],
            ),
        ),
    ],
)
async def test_migrate(db, collection_name, fixture_name, create_data, check_object):
    doc = deepcopy(get_fixture_json(fixture_name))
    db_collection = db.get_collection(collection_name)
    create_data(doc)
    await db_collection.insert_one(doc)

    await migrate_collection_tags(TAG_DATA["code"], collection_name)

    doc_data = await db_collection.find_one({"_id": doc["_id"]})
    assert all(check_object(doc_data, doc))
