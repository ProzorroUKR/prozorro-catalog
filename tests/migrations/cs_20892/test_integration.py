from copy import deepcopy
from uuid import uuid4

import pytest

from catalog.migrations.cs_20892_update_duplicate_dateModified import migrate_collection_dateModified
from tests.utils import get_fixture_json


@pytest.mark.parametrize(
    ("collection_name", "fixture_name"),
    [
        pytest.param("category", "category"),
        pytest.param("profiles", "profile"),
        pytest.param("products", "product"),
        pytest.param("offers", "offer"),
        pytest.param("vendors", "vendor"),
        pytest.param("contributors", "contributor"),
        pytest.param("requests", "product_request"),
    ],
)
async def test_migrate(db, collection_name, fixture_name):
    doc = deepcopy(get_fixture_json(fixture_name))
    dt = "2025-01-01T00:00:00+02:00"
    doc_1 = {
        **doc,
        "_id": uuid4().hex,
        "dateModified": dt,
    }
    await db.get_collection(collection_name).insert_one(doc_1)
    doc_2 = {
        **doc,
        "_id": uuid4().hex,
        "dateModified": dt,
    }
    await db.get_collection(collection_name).insert_one(doc_2)
    doc_3 = {
        **doc,
        "_id": uuid4().hex,
        "dateModified": "2025-01-01T00:00:01+03:00",
    }
    await db.get_collection(collection_name).insert_one(doc_3)

    await migrate_collection_dateModified(collection_name)

    doc_1_data = await db.get_collection(collection_name).find_one({"_id": doc_1["_id"]})
    assert doc_1_data.get("dateModified") != doc_1.get("dateModified")

    doc_2_data = await db.get_collection(collection_name).find_one({"_id": doc_2["_id"]})
    assert doc_2_data.get("dateModified") != doc_2.get("dateModified")

    assert doc_1_data.get("dateModified") != doc_2_data.get("dateModified")

    # doc not changed
    doc_3_data = await db.get_collection(collection_name).find_one({"_id": doc_3["_id"]})
    assert doc_3_data.get("dateModified") == doc_3.get("dateModified")
