from .base import TEST_AUTH, TEST_AUTH_ANOTHER, TEST_AUTH_NO_PERMISSION
from catalog.doc_service import generate_test_url


async def test_vendor_create_no_permission(api):
    test_vendor = api.get_fixture_json('vendor')
    test_vendor.pop("categories")
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH_NO_PERMISSION,
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'vendors' write operation"]} == result


async def test_vendor_create_without_category(api):
    test_vendor = api.get_fixture_json('vendor')
    test_vendor.pop("categories")
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['field required: data.categories']} == result

    test_vendor["categories"] = []
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['ensure this value has at least 1 items: data.categories']} == result


async def test_vendor_create_with_404_category(api):
    test_vendor = api.get_fixture_json('vendor')
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 404, result
    assert {'errors': ['Category not found']} == result


async def test_vendor_create_with_hidden_category(api, mock_agreement):
    data = api.get_fixture_json('category')
    data["status"] = "hidden"
    resp = await api.put(
        f"/api/categories/{data['id']}",
        json={"data": data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    category = await resp.json()
    assert category["data"]["status"] == "hidden"
    category_id = category["data"]["id"]

    test_vendor = api.get_fixture_json('vendor')
    test_vendor["categories"] = [{"id": category_id}]

    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': [f'Category {category_id} is not active']} == result


async def test_vendor_without_region(api, category):
    data = api.get_fixture_json('vendor')
    data['categories'] = [{"id": category["data"]["id"]}]
    # 1
    data['vendor']["address"].pop("region")
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['field required: data.vendor.address.region']} == result

    # 2
    data['vendor']["address"]["countryName"] = "Антарктика"
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['field required: data.vendor.address.region']} == result


async def test_vendor_ukrainian_region_dictionary(api, category):
    data = api.get_fixture_json('vendor')
    data['categories'] = [{"id": category["data"]["id"]}]
    data['vendor']["address"] = {
      "countryName": "Україна",
      "region": "невідомий"
    }
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of classifiers/ua_regions.json: data.vendor.address.region']} == result


async def test_vendor_create(api, mock_agreement):
    data = api.get_fixture_json('category')
    resp = await api.put(
        f"/api/categories/{data['id']}",
        json={"data": data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    category = await resp.json()

    test_vendor = api.get_fixture_json('vendor')
    test_vendor["categories"] = [{"id": category["data"]["id"]}]
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result
    assert "access" in result
    assert "owner" in result["access"]
    assert "token" in result["access"]

    assert "data" in result
    data = result["data"]

    # check passed data
    for k, v in test_vendor.items():
        assert data[k] == v

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in test_vendor}
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'dateModified', 'owner', 'isActivated', "status"}
    assert data["isActivated"] is False
    assert data["status"] == "pending"


async def test_vendor_patch(api, category):
    data = api.get_fixture_json('vendor')
    data['categories'] = [{"id": category["data"]["id"]}]
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    vendor, access = result["data"], result["access"]

    patch_data = {"isActivated": False}
    resp = await api.patch(
        '/api/vendors/1',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 404

    uid = vendor["id"]
    resp = await api.patch(
        f'/api/vendors/{uid}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ['activation is only allowed action: data.isActivated']}

    patch_data = {"isActivated": True}
    resp = await api.patch(
        f'/api/vendors/{uid}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 401
    result = await resp.json()
    assert result == {'errors': ['Require access token']}

    resp = await api.patch(
        f'/api/vendors/{uid}?access_token=паляміта',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 403
    result = await resp.json()
    assert result == {'errors': ['Access token mismatch']}

    resp = await api.patch(
        f'/api/vendors/{uid}?access_token={access["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH_ANOTHER,
    )
    assert resp.status == 403
    result = await resp.json()
    assert result == {'errors': ['Owner mismatch']}

    assert vendor["isActivated"] is False
    resp = await api.patch(
        f'/api/vendors/{uid}?access_token={access["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    result = await resp.json()
    assert result["data"]["isActivated"] is True
    assert result["data"]["dateModified"] > vendor["dateModified"]
    assert result["data"]["dateCreated"] == vendor["dateCreated"]

    resp = await api.patch(
        f'/api/vendors/{uid}?access_token={access["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    result2 = await resp.json()
    assert result["data"]["dateModified"] == result2["data"]["dateModified"]


async def test_vendor_duplicate(api, category):
    data = api.get_fixture_json('vendor')
    data['categories'] = [{"id": category["data"]["id"]}]
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    vendor, access = result["data"], result["access"]

    # try create second draft
    resp2 = await api.post(
        '/api/vendors',
        json={"data": data},
        auth=TEST_AUTH,
    )
    result2 = await resp2.json()
    assert resp2.status == 201, result2
    vendor2, access2 = result2["data"], result2["access"]

    # first vendor activation
    patch_data = {"isActivated": True}
    assert vendor["isActivated"] is False
    resp = await api.patch(
        f'/api/vendors/{vendor["id"]}?access_token={access["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    result = await resp.json()
    assert result["data"]["isActivated"] is True

    # try to activate second draft
    resp = await api.patch(
        f'/api/vendors/{result2["data"]["id"]}?access_token={access2["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    result_duplicate = await resp.json()
    assert resp.status == 400, result_duplicate
    identifier_id = data["vendor"]["identifier"]["id"]
    expected = {'errors': [f'Cannot activate vendor.identifier.id {identifier_id} already exists: {vendor["id"]}']}
    assert expected == result_duplicate

    # try create third draft
    resp = await api.post(
        '/api/vendors',
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    expected = {'errors': [f'Cannot create vendor.identifier.id {identifier_id} already exists: {vendor["id"]}']}
    assert resp.status == 400, result
    assert expected == result


async def test_vendor_get(api, vendor):
    vendor, access = vendor["data"], vendor["access"]
    resp = await api.get(f'/api/vendors/{vendor["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'categories', 'id', 'vendor', 'owner', "status",
                                          'isActivated', 'dateCreated', 'dateModified'}
    assert result["data"]["status"] == "active"


async def test_vendor_get_for_sign(api, vendor):
    vendor, access = vendor["data"], vendor["access"]

    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/documents',
        json={
            "data": doc_data,
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    doc_data = result["data"]

    resp = await api.get(f'/api/sign/vendors/{vendor["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'categories', 'vendor', 'documents'}

    doc_result = result["data"]["documents"][0]
    assert {"url", "title", "format", "hash"} == set(doc_result.keys())


async def test_vendor_list(api, vendor):
    vendor, _ = vendor["data"], vendor["access"]
    resp = await api.get(f'/api/vendors')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data', 'next_page'}
    assert len(result["data"]) == 1
    assert set(result["data"][0].keys()) == {'dateModified', 'id'}
    assert result["data"][0]["id"] == vendor["id"]

    # adding inactive one
    test_vendor = api.get_fixture_json('vendor')
    test_vendor["categories"] = vendor["categories"]
    test_vendor["vendor"]["identifier"]["id"] = "1234"
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    assert result["data"]["isActivated"] is False

    # still only one
    resp = await api.get(f'/api/vendors')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]) == 1
    assert vendor["id"] == result["data"][0]["id"]


async def test_create_vendor_with_invalid_identifier(api):
    test_vendor = api.get_fixture_json('vendor')
    test_vendor['vendor']['identifier']['scheme'] = 'SOME_CODE'
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': [
        'must be one of organizations/identifier_scheme.json codes: data.vendor.identifier.scheme'
    ]} == result

