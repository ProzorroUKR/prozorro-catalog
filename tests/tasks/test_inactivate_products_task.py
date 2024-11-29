from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from catalog.utils import get_now
from cron.inactivate_products_task import run_task
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
)


async def test_migrate_products(db, api):
    product_fixture = deepcopy(get_fixture_json("product"))
    product_fixture["dateModified"] = "2024-06-06T06:00:00+03:00"

    product_inactive = deepcopy(product_fixture)
    product_inactive["_id"] = uuid4().hex
    product_inactive["status"] = "inactive"
    await db.products.insert_one(product_inactive)

    product_hidden = deepcopy(product_fixture)
    product_hidden["_id"] = uuid4().hex
    product_hidden["status"] = "hidden"
    await db.products.insert_one(product_hidden)

    product_active_wo_expiration_date = deepcopy(product_fixture)
    product_active_wo_expiration_date["_id"] = uuid4().hex
    await db.products.insert_one(product_active_wo_expiration_date)

    product_active_with_expiration_date = deepcopy(product_fixture)
    product_active_with_expiration_date["_id"] = uuid4().hex
    product_active_with_expiration_date["expirationDate"] = (get_now() - timedelta(minutes=1)).isoformat()
    await db.products.insert_one(product_active_with_expiration_date)

    vendor_product_active_with_expiration_date = deepcopy(product_fixture)
    vendor_product_active_with_expiration_date["_id"] = uuid4().hex
    vendor_product_active_with_expiration_date["vendor"] = {"id": uuid4().hex}
    vendor_product_active_with_expiration_date["expirationDate"] = (get_now() - timedelta(minutes=1)).isoformat()
    await db.products.insert_one(vendor_product_active_with_expiration_date)

    await run_task()

    product_data = await db.products.find_one({"_id": product_inactive["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data["dateModified"] == product_inactive["dateModified"]

    product_data = await db.products.find_one({"_id": product_hidden["_id"]})
    assert product_data["status"] == "hidden"
    assert product_data["dateModified"] == product_hidden["dateModified"]

    product_data = await db.products.find_one({"_id": product_active_wo_expiration_date["_id"]})
    assert product_data["status"] == "active"
    assert product_data["dateModified"] == product_active_wo_expiration_date["dateModified"]

    product_data = await db.products.find_one({"_id": product_active_with_expiration_date["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data["dateModified"] != product_active_with_expiration_date["dateModified"]

    product_data = await db.products.find_one({"_id": vendor_product_active_with_expiration_date["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data["dateModified"] != vendor_product_active_with_expiration_date["dateModified"]
