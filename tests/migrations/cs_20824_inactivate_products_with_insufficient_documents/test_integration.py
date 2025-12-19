from copy import deepcopy
from unittest.mock import Mock
from uuid import uuid4

from catalog.migrations.cs_20824_inactivate_products_with_insufficient_documents import migrate
from catalog.settings import DOC_SERVICE_URL
from tests.integration.conftest import get_fixture_json


async def test_migrate(db):
    product = deepcopy(get_fixture_json("vendor_product"))
    # no vendor
    product_1 = {
        **product,
        "_id": uuid4().hex,
        "dateCreated": "2025-12-11T23:59:59+02:00",
        "dateModified": "2025-12-11T23:59:59+02:00",
        "expirationDate": "2025-12-11T23:59:59+02:00",
        "status": "active",
    }
    await db.products.insert_one(product_1)
    # no docs
    product_2 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateCreated": "2025-12-11T23:59:59+02:00",
        "dateModified": "2025-12-11T23:59:59+02:00",
        "expirationDate": "2025-12-11T23:59:59+02:00",
        "status": "active",
    }
    await db.products.insert_one(product_2)
    # 5 docs excluding sign.p7s
    product_3 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateCreated": "2025-12-11T23:59:59+02:00",
        "dateModified": "2025-12-11T23:59:59+02:00",
        "expirationDate": "2025-12-11T23:59:59+02:00",
        "status": "active",
        "documents": [
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "sign.p7s"
            }
        ],
    }
    await db.products.insert_one(product_3)
    # date created over 2025-12-11
    product_4 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateCreated": "2025-12-12T00:00:00+02:00",
        "dateModified": "2025-12-12T00:00:00+02:00",
        "expirationDate": "2025-12-12T00:00:00+02:00",
        "status": "active",
        "documents": [],
    }
    await db.products.insert_one(product_4)
    # 6 docs excluding sign.p7s
    product_5 = {
        **product,
        "_id": uuid4().hex,
        "vendor": {},
        "dateCreated": "2025-12-11T23:59:59+02:00",
        "dateModified": "2025-12-11T23:59:59+02:00",
        "expirationDate": "2025-12-11T23:59:59+02:00",
        "status": "active",
        "documents": [
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "test"
            },
            {
                "title": "sign.p7s"
            }
        ],
    }
    await db.products.insert_one(product_5)
    # hidden
    product_6 = {
        **product,
        "_id": uuid4().hex,
        "dateCreated": "2025-12-11T23:59:59+02:00",
        "dateModified": "2025-12-11T23:59:59+02:00",
        "expirationDate": "2025-12-11T23:59:59+02:00",
        "status": "hidden",
    }
    await db.products.insert_one(product_6)

    await migrate(
        Mock(
            doc_url=f"{DOC_SERVICE_URL}/get/ed2d519757304fa9a89a319661cc693e?KeyID=a8968c46&Signature=3lI2VcU48qmxUZ%252BoGFu7bDA8VVamiDjEZz7%252BpZutaUrV%252BFCqNztGzTsL5kNVXm%2FdgRlGAPk%252B1HbreX7NhvnOBw%253D%253D",
            doc_hash="md5:ea398604479040a989a7808402edc874",
            doc_format="application/pdf",
            doc_title="Протокол для -022 -с.pdf",
        )
    )

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data["status"] == "active"
    assert product_data.get("dateModified") == product_1.get("dateModified")
    assert product_data.get("expirationDate") == product_1.get("expirationDate")
    assert product_data.get("documents") == product_1.get("documents")

    product_data = await db.products.find_one({"_id": product_2["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data.get("dateModified") != product_2.get("dateModified")
    assert product_data.get("expirationDate") != product_2.get("expirationDate")
    new_doc = product_data["documents"][-1]
    assert new_doc == {
        "dateModified": product_data["dateModified"],
        "datePublished": product_data["dateModified"],
        "format": "application/pdf",
        "hash": "md5:ea398604479040a989a7808402edc874",
        "id": new_doc["id"],
        "title": "Протокол для -022 -с.pdf",
        "url": f"/api/products/{product_2["_id"]}/documents/{new_doc["id"]}?download=ed2d519757304fa9a89a319661cc693e",
    }

    product_data = await db.products.find_one({"_id": product_3["_id"]})
    assert product_data["status"] == "inactive"
    assert product_data.get("dateModified") != product_3.get("dateModified")
    assert product_data.get("expirationDate") != product_3.get("expirationDate")
    new_doc = product_data["documents"][-1]
    assert new_doc == {
        "dateModified": product_data["dateModified"],
        "datePublished": product_data["dateModified"],
        "format": "application/pdf",
        "hash": "md5:ea398604479040a989a7808402edc874",
        "id": new_doc["id"],
        "title": "Протокол для -022 -с.pdf",
        "url": f"/api/products/{product_3["_id"]}/documents/{new_doc["id"]}?download=ed2d519757304fa9a89a319661cc693e",
    }

    product_data = await db.products.find_one({"_id": product_4["_id"]})
    assert product_data["status"] == "active"
    assert product_data.get("dateModified") == product_4.get("dateModified")
    assert product_data.get("expirationDate") == product_4.get("expirationDate")
    assert product_data.get("documents") == product_4.get("documents")

    product_data = await db.products.find_one({"_id": product_5["_id"]})
    assert product_data["status"] == "active"
    assert product_data.get("dateModified") == product_5.get("dateModified")
    assert product_data.get("expirationDate") == product_5.get("expirationDate")
    assert product_data.get("documents") == product_5.get("documents")

    product_data = await db.products.find_one({"_id": product_6["_id"]})
    assert product_data["status"] == "hidden"
    assert product_data.get("dateModified") == product_6.get("dateModified")
    assert product_data.get("expirationDate") == product_6.get("expirationDate")
    assert product_data.get("documents") == product_6.get("documents")
