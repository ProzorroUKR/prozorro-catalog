from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_18012_inactivate_vendor_products import (
    migrate,
)
from tests.integration.conftest import api, db, get_fixture_json


async def test_inactivate_vendor_products(db, api):
    product_non_localized = deepcopy(get_fixture_json("product"))
    product_non_localized["_id"] = uuid4().hex
    product_non_localized["dateModified"] = "2024-04-01T10:00:00+02:00"
    await db.products.insert_one(product_non_localized)

    product_loc_active_old = deepcopy(get_fixture_json("product"))
    product_loc_active_old.update({
        "_id": uuid4().hex,
        "vendor": {"id": uuid4().hex},
        "dateCreated": "2022-01-01",
        "status": "active",
        "dateModified": "2024-04-01T10:00:00+02:00",
    })
    await db.products.insert_one(product_loc_active_old)

    product_loc_hidden_old = deepcopy(product_loc_active_old)
    product_loc_hidden_old.update({
        "_id": uuid4().hex,
        "status": "hidden",
    })
    await db.products.insert_one(product_loc_hidden_old)

    product_loc_active_new = deepcopy(product_loc_active_old)
    product_loc_active_new.update({
        "_id": uuid4().hex,
        "dateCreated": "2024-01-01",
    })
    await db.products.insert_one(product_loc_active_new)

    product_loc_hidden_new = deepcopy(product_loc_active_old)
    product_loc_hidden_new.update({
        "_id": uuid4().hex,
        "dateCreated": "2024-01-01",
        "status": "hidden",
    })
    await db.products.insert_one(product_loc_hidden_new)

    await migrate()

    product_data = await db.products.find_one({"_id": product_non_localized["_id"]})
    assert product_data["status"] == "active"
    assert "expirationDate" not in product_data

    product_data = await db.products.find_one({"_id": product_loc_active_old["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data["expirationDate"] == "2022-12-31T23:59:59+02:00"
    assert product_data["dateModified"] != product_loc_active_old["dateModified"]

    product_data = await db.products.find_one({"_id": product_loc_hidden_old["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data["expirationDate"] == "2022-12-31T23:59:59+02:00"
    assert product_data["dateModified"] != product_loc_hidden_old["dateModified"]

    product_data = await db.products.find_one({"_id": product_loc_active_new["_id"]})
    assert product_data["status"] == "active"
    assert product_data["expirationDate"] == "2024-12-31T23:59:59+02:00"
    assert product_data["dateModified"] != product_loc_active_new["dateModified"]

    product_data = await db.products.find_one({"_id": product_loc_hidden_new["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data["expirationDate"] == "2024-12-31T23:59:59+02:00"
    assert product_data["dateModified"] != product_loc_hidden_new["dateModified"]
