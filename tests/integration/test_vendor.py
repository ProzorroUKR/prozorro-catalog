from copy import deepcopy
from random import randint
from urllib.parse import quote
from .base import TEST_AUTH_NO_PERMISSION, TEST_AUTH, TEST_AUTH_ANOTHER


async def test_vendor_create(api):
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
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'dateModified', 'owner', 'isActive'}
    assert data["isActive"] is False


async def test_vendor_patch(api, vendor):
    vendor, access = vendor["data"], vendor["access"]

    patch_data = {"isActive": False}
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
    assert result == {'errors': ['activation is only allowed action: data.isActive']}

    patch_data = {"isActive": True}
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

    assert vendor["isActive"] is False
    resp = await api.patch(
        f'/api/vendors/{uid}?access_token={access["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    result = await resp.json()
    assert result["data"]["isActive"] is True
    assert result["data"]["dateModified"] > vendor["dateModified"]
    assert result["data"]["dateCreated"] == vendor["dateCreated"]


async def test_vendor_get(api, vendor):
    vendor, access = vendor["data"], vendor["access"]
    resp = await api.get(f'/api/vendors/{vendor["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'categories', 'id', 'vendor', 'owner',
                                          'isActive', 'dateCreated', 'dateModified'}


async def test_vendor_list(api, vendor):
    vendor, _ = vendor["data"], vendor["access"]
    resp = await api.get(f'/api/vendors')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data', 'next_page'}
    assert len(result["data"]) == 1
    assert set(result["data"][0].keys()) == {'dateModified', 'id'}
    assert result["data"][0]["id"] == vendor["id"]
