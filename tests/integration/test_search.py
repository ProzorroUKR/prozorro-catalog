from random import randint
from collections import defaultdict
from uuid import uuid4
from .base import TEST_AUTH


async def test_search(api):
    ids = defaultdict(list)

    # prepare objects
    category = api.get_fixture_json('category')
    profile = api.get_fixture_json('profile')
    product = api.get_fixture_json('product')
    offer = api.get_fixture_json('offer')
    for i in range(10):
        category_id = f"33190000-000{i}-10033300"
        category['id'] = category_id
        resp = await api.put(
            f"/api/categories/{category_id}",
            json={"data": category},
            auth=TEST_AUTH
        )
        assert resp.status == 201, await resp.json()
        category_access = (await resp.json())["access"]
        ids["category"].append(category_id)

        profile_id = '{}-{}'.format(randint(100000, 900000), category_id)
        profile['id'] = profile_id
        profile['relatedCategory'] = category["id"]
        resp = await api.put(
            f"/api/profiles/{profile_id}",
            json={"data": profile,
                  "access": category_access},
            auth=TEST_AUTH,
        )
        assert resp.status == 201, await resp.json()
        profile_access = (await resp.json())["access"]
        ids["profile"].append(profile_id)

        product_id = f"{product['classification']['id'][:4]}-{product['brand']['name'][:4]}-" \
            f"{product['identifier']['id'][:13]}-00000{i}"
        product['id'] = product_id
        product['relatedProfile'] = profile["id"]
        resp = await api.put(
            f"/api/products/{product_id}",
            json={"data": product,
                  "access": profile_access},
            auth=TEST_AUTH,
        )
        assert resp.status == 201, await resp.json()
        ids["product"].append(product_id)

        offer_id = uuid4().hex
        offer['relatedProduct'] = product["id"]
        resp = await api.put(
            f"/api/offers/{offer_id}",
            json={"data": offer},
            auth=TEST_AUTH,
        )
        assert resp.status == 201, await resp.json()
        ids["offer"].append(offer_id)

    # test
    resp = await api.post(
        f"/api/search",
        json={"data": {
            "resource": "category",
            "ids": ids["category"][2:5],
        }},
    )
    assert resp.status == 201, await resp.json()
    data = (await resp.json())["data"]
    assert set(i["id"] for i in data) == set(ids["category"][2:5])

    resp = await api.post(
        f"/api/search",
        json={"data": {
            "resource": "profile",
            "ids": ids["profile"][:3],
        }},
    )
    assert resp.status == 201, await resp.json()
    data = (await resp.json())["data"]
    assert set(i["id"] for i in data) == set(ids["profile"][:3])

    resp = await api.post(
        f"/api/search",
        json={"data": {
            "resource": "product",
            "ids": ids["product"][8:],
        }},
    )
    assert resp.status == 201, await resp.json()
    data = (await resp.json())["data"]
    assert set(i["id"] for i in data) == set(ids["product"][8:])

    resp = await api.post(
        f"/api/search",
        json={"data": {
            "resource": "offer",
            "ids": ids["offer"][7:9],
        }},
    )
    assert resp.status == 201, await resp.json()
    data = (await resp.json())["data"]
    assert set(i["id"] for i in data) == set(ids["offer"][7:9])