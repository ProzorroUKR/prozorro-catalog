from copy import deepcopy
from unittest.mock import Mock

from bson import ObjectId

from catalog.migrations.cs_20828_hide_category import migrate as migrate_hide_categories
from catalog.migrations.cs_20828_patch_compressor_category import migrate as migrate_compressor_category
from tests.integration.conftest import get_fixture_json


async def test_migrate_patch_compressor_category(db):
    old_category_id = ObjectId()
    old_category = deepcopy(get_fixture_json("category"))
    old_category["_id"] = old_category_id
    await db.category.insert_one(old_category)

    new_category_id = ObjectId()
    new_category = deepcopy(get_fixture_json("category"))
    new_category["_id"] = new_category_id
    await db.category.insert_one(new_category)

    product = deepcopy(get_fixture_json("vendor_product"))

    # product for update
    product_1 = {
        **product,
        "_id": ObjectId(),
        "dateModified": "2025-12-25T12:00:00+02:00",
        "relatedCategory": old_category_id,
    }
    await db.products.insert_one(product_1)

    # relatedCategory does not match
    product_2 = {
        **product,
        "_id": ObjectId(),
        "dateModified": "2025-12-25T12:00:00+02:00",
        "relatedCategory": ObjectId(),
    }
    await db.products.insert_one(product_2)

    await migrate_compressor_category(
        Mock(
            id=new_category_id,
            old_id=old_category_id,
        )
    )

    category_data = await db.category.find_one({"_id": new_category_id})
    assert category_data.get("dateModified") != new_category.get("dateModified")
    assert (
        category_data.get("description")
        == "Насоси та компресори"
        != new_category.get("description")
    )
    assert (
        category_data.get("title")
        == "Насоси та компресори"
        != new_category.get("title")
    )

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data.get("dateModified") != product_1.get("dateModified")
    assert (
        product_data.get("relatedCategory")
        == new_category_id
        != product_1.get("relatedCategory")
    )

    product_data = await db.products.find_one({"_id": product_2["_id"]})
    assert product_data.get("dateModified") == product_2.get("dateModified")
    assert (
        product_data.get("relatedCategory")
        == product_2.get("relatedCategory")
        != new_category_id
    )


async def test_migrate_hide_category(db):
    category_1 = deepcopy(get_fixture_json("category"))
    category_1["_id"] = ObjectId()
    await db.category.insert_one(category_1)

    category_2 = deepcopy(get_fixture_json("category"))
    category_2["_id"] = ObjectId()
    await db.category.insert_one(category_2)

    category_3 = deepcopy(get_fixture_json("category"))
    category_3["_id"] = ObjectId()
    await db.category.insert_one(category_3)

    await migrate_hide_categories(Mock(id=[category_1["_id"], category_3["_id"]]))

    category_data = await db.category.find_one({"_id": category_1["_id"]})
    assert category_data.get("dateModified") != category_1.get("dateModified")
    assert category_data.get("status") == "hidden"

    category_data = await db.category.find_one({"_id": category_2["_id"]})
    assert category_data.get("dateModified") == category_1.get("dateModified")
    assert category_data.get("status") != "hidden"

    category_data = await db.category.find_one({"_id": category_3["_id"]})
    assert category_data.get("dateModified") != category_3.get("dateModified")
    assert category_data.get("status") == "hidden"
