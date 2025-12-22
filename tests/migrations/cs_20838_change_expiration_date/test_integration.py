from copy import deepcopy
from unittest.mock import Mock
from uuid import uuid4

from catalog.migrations.cs_20838_change_expiration_date import migrate
from tests.integration.conftest import get_fixture_json


async def test_migrate(db):
    product = deepcopy(get_fixture_json("vendor_product"))
    old_exp_date = "2025-12-31T23:59:59+02:00"
    new_exp_date = "2026-03-31T23:59:59+03:00"
    # no vendor
    product_1 = {
        **product,
        "_id": uuid4().hex,
        "dateModified": old_exp_date,
        "expirationDate": old_exp_date,
        "status": "active",
    }
    await db.products.insert_one(product_1)
    # expiration date does not match
    product_2 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateModified": old_exp_date,
        "expirationDate": "2027-03-31T23:59:59+03:00",
        "status": "active",
    }
    await db.products.insert_one(product_2)
    # hidden
    product_3 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateModified": old_exp_date,
        "expirationDate": old_exp_date,
        "status": "hidden",
    }
    await db.products.insert_one(product_3)
    # correct product
    product_4 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateModified": old_exp_date,
        "expirationDate": old_exp_date,
        "status": "active",
    }
    await db.products.insert_one(product_4)

    await migrate(
        Mock(
            old_expiration_date=old_exp_date,
            new_expiration_date=new_exp_date,
        )
    )

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data["status"] == "active"
    assert product_data.get("dateModified") == product_1.get("dateModified")
    assert product_data.get("expirationDate") == product_1.get("expirationDate")

    product_data = await db.products.find_one({"_id": product_2["_id"]})
    assert product_data["status"] == "active"
    assert product_data.get("dateModified") == product_2.get("dateModified")
    assert product_data.get("expirationDate") == product_2.get("expirationDate")

    product_data = await db.products.find_one({"_id": product_3["_id"]})
    assert product_data["status"] == "hidden"
    assert product_data.get("dateModified") == product_3.get("dateModified")
    assert product_data.get("expirationDate") == product_3.get("expirationDate")

    product_data = await db.products.find_one({"_id": product_4["_id"]})
    assert product_data["status"] == "active"
    assert product_data.get("dateModified") != product_4.get("dateModified")
    assert product_data.get("expirationDate") != product_4.get("expirationDate")
    assert product_data.get("expirationDate") == new_exp_date
