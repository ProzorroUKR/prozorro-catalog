from .base import TEST_AUTH, TEST_AUTH_ANOTHER, TEST_AUTH_NO_PERMISSION
from catalog.doc_service import generate_test_url


async def test_vendor_create_no_permission(api):
    test_vendor = api.get_fixture_json('vendor')
    resp = await api.post(
        '/api/vendors',
        json={"data": test_vendor},
        auth=TEST_AUTH_NO_PERMISSION,
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'vendors' write operation"]} == result


async def test_vendor_without_region(api):
    data = api.get_fixture_json('vendor')
    # 1
    data['vendor']["address"].pop("region")
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Field required: data.vendor.address.region']} == result

    # 2
    data['vendor']["address"]["countryName"] = "Антарктика"
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Field required: data.vendor.address.region']} == result


async def test_vendor_ukrainian_region_dictionary(api):
    data = api.get_fixture_json('vendor')
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
    assert {'errors': ['Value error, must be one of classifiers/ua_regions.json: data.vendor.address.region']} == result


async def test_vendor_create(db, api, mock_agreement):
    test_vendor = api.get_fixture_json('vendor')
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
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'dateModified', 'owner', 'isActivated', 'status'}
    assert data["isActivated"] is False
    assert data["status"] == "pending"


async def test_vendor_patch(db, api):
    data = api.get_fixture_json('vendor')
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
    assert result == {'errors': ['Assertion failed, activation is only allowed action: data.isActivated']}

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


async def test_vendor_duplicate(db, api):
    data = api.get_fixture_json('vendor')
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    vendor, access = result["data"], result["access"]

    # try to create second draft
    resp = await api.post(
        '/api/vendors',
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    identifier_id = data["vendor"]["identifier"]["id"]
    expected = {'errors': [f'Cannot create vendor.identifier.id {identifier_id} already exists: {vendor["id"]}']}
    assert resp.status == 400, result
    assert expected == result


async def test_vendor_get(api, vendor):
    vendor, access = vendor["data"], vendor["access"]
    resp = await api.get(f'/api/vendors/{vendor["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'id', 'vendor', 'owner', 'status',
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
    assert set(result["data"].keys()) == {'vendor', 'documents'}

    doc_result = result["data"]["documents"][0]
    assert {"url", "title", "format", "hash"} == set(doc_result.keys())


async def test_vendor_list(db, api, vendor):
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
        'Value error, must be one of organizations/identifier_scheme.json codes: data.vendor.identifier.scheme'
    ]} == result

