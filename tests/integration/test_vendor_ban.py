from copy import deepcopy

from aiohttp import BasicAuth
from freezegun import freeze_time

from urllib.parse import urlparse, parse_qsl, urlencode
from catalog.doc_service import generate_test_url, get_doc_service_uid_from_url
from catalog.models.vendor import VendorStatus
from catalog.utils import get_now
from cron.activate_banned_vendors import run_task as activate_banned_vendors
from .base import TEST_AUTH, TEST_AUTH_CPB
from .conftest import set_requirements_to_responses


async def test_create_ban_by_not_market_administrator(api, vendor):
    data = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    data['documents'][0]['url'] = generate_test_url(doc_hash)
    data['documents'][0]['hash'] = f"md5:{doc_hash}"
    data['administrator']['identifier']['id'] = '12121212'
    del data["dueDate"]
    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of market administrators: data.administrator.identifier']} == result


async def test_create_ban_permission(api, vendor):
    data = api.get_fixture_json('ban')
    del data["dueDate"]
    doc_hash = "0" * 32
    data['documents'][0]['url'] = generate_test_url(doc_hash)
    data['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/bans",
        json={"data": data},
        auth=BasicAuth(login="boo"),
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ['Access token mismatch']} == result


async def test_ban_create_invalid_fields(api, vendor):
    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/bans",
        json={"data": {}},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 400, result
    errors = [
        'field required: data.reason',
        'field required: data.administrator',
    ]
    assert {'errors': errors} == result

    data = deepcopy(api.get_fixture_json('ban'))
    del data["dueDate"]
    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Can add document only from document service: data.documents.0.__root__']} == result

    data['documents'][0]['url'] = generate_test_url(data["documents"][0]["hash"])
    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Document url signature is invalid: data.documents.0.__root__']} == result

    del data["documents"]
    data["reason"] = "some other reason"
    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of market/ban_reason.json keys: data.reason']} == result


async def test_ban_create(api, vendor):
    test_ban = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    test_ban['documents'][0]['url'] = generate_test_url(doc_hash)
    test_ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    del test_ban["dueDate"]
    resp = await api.post(
        f"api/vendors/{vendor['data']['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()

    assert resp.status == 201, result
    assert "data" in result
    data = result["data"]
    assert "owner" in result["data"]

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in test_ban}
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'owner', 'dueDate'}

    # check quantity of bans in vendor object
    resp = await api.get(f"/api/vendors/{vendor['data']['id']}")
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]["bans"]) == 1
    assert result["data"]["status"] == VendorStatus.banned

    now = get_now()
    with freeze_time(now.replace(year=now.year + 1).isoformat()):
        await activate_banned_vendors()
        resp = await api.get(f"api/vendors/{vendor['data']['id']}")
        result = await resp.json()
        assert result["data"]["status"] == VendorStatus.active


async def test_ban_get(api, vendor, vendor_ban):
    resp = await api.get(f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {
        'id', 'reason', 'owner', 'dateCreated', 'description', 'administrator', 'documents', 'dueDate'
    }


async def test_bans_list(api, vendor, vendor_ban):
    resp = await api.get(f'/api/vendors/{vendor["data"]["id"]}/bans')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]) == 1
    assert set(result["data"][0].keys()) == {
        'id', 'reason', 'owner', 'dateCreated', 'description', 'administrator', 'documents', 'dueDate'
    }
    assert result["data"][0]["id"] == vendor_ban["data"]["id"]


async def test_ban_already_exists(api, vendor):
    test_ban = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    test_ban['documents'][0]['url'] = generate_test_url(doc_hash)
    test_ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    del test_ban["dueDate"]
    resp = await api.post(
        f"api/vendors/{vendor['data']['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()

    assert resp.status == 201, result

    # add new ban before dueDate
    resp = await api.post(
        f"api/vendors/{vendor['data']['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ['Vendor is banned']} == result


async def test_vendor_banned(api, vendor, vendor_ban, category):
    category_id = category['data']['id']

    vendor_token = vendor['access']['token']
    vendor = vendor['data']

    test_product = api.get_fixture_json('vendor_product')
    test_product['relatedCategory'] = category_id
    set_requirements_to_responses(test_product['requirementResponses'], category)

    # check vendor is banned
    resp = await api.get(f"/api/vendors/{vendor['id']}")
    assert resp.status == 200
    result = await resp.json()
    assert result["data"]["status"] == VendorStatus.banned

    # try to add product from banned vendor
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 403
    result = await resp.json()
    assert result == {'errors': ['Vendor is banned']}

    # a year is passed
    now = get_now()
    with freeze_time(now.replace(year=now.year + 1).isoformat()):
        await activate_banned_vendors()
        resp = await api.get(f"api/vendors/{vendor['id']}")
        result = await resp.json()
        assert result["data"]["status"] == VendorStatus.active

        resp = await api.post(
            f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
            json={'data': test_product},
            auth=TEST_AUTH,
        )

        assert resp.status == 201


async def test_ban_inactive_vendor(api, category):
    data = api.get_fixture_json('vendor')
    data['categories'] = [{"id": category["data"]["id"]}]
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    vendor = result["data"]

    test_ban = api.get_fixture_json('ban')
    del test_ban["documents"]
    del test_ban["dueDate"]
    resp = await api.post(
        f"api/vendors/{vendor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH_CPB,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ['Vendor should be activated.']}


# documents
async def test_vendor_ban_doc_create(api, vendor, vendor_ban):
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 201, result
    data = result["data"]
    ds_uid = get_doc_service_uid_from_url(doc_data["url"])
    expected = f"{api.server.scheme}://{api.server.host}:{api.server.port}" \
        f"/api/vendors/{vendor['data']['id']}/bans/{vendor_ban['data']['id']}/documents/{data['id']}?download={ds_uid}"
    assert expected == data["url"]

    resp = await api.get(f'/api/vendors/{vendor["data"]["id"]}')
    assert resp.status == 200, result
    assert result["data"]["dateModified"] == data["dateModified"]


async def test_vendor_ban_doc_put(api, vendor, vendor_ban):
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH_CPB,
    )
    response = await resp.json()
    doc_before_put = response["data"]
    doc_hash = "1" * 32
    doc_data = {
        "title": "name1.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.put(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents/{doc_before_put["id"]}',
        json={"data": doc_data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 201, result
    doc_after_put = result["data"]
    assert doc_before_put["dateModified"] != doc_after_put["dateModified"]
    assert doc_before_put["url"].split("?")[0] == doc_after_put["url"].split("?")[0]
    assert doc_before_put["url"] != doc_after_put["url"]
    assert doc_before_put["datePublished"] != doc_after_put["datePublished"]
    assert doc_after_put["url"].split("/")[-2] == "documents"

    resp = await api.get(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents/{doc_before_put["id"]}',
    )
    assert resp.status == 200, result
    assert result["data"] == doc_after_put

    resp = await api.get(f'/api/vendors/{vendor["data"]["id"]}')
    assert resp.status == 200, result
    assert result["data"]["dateModified"] == doc_after_put["dateModified"]


async def test_vendor_ban_doc_patch(api, vendor, vendor_ban):
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH_CPB,
    )
    response = await resp.json()
    doc_before_patch = response["data"]

    resp = await api.patch(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents/{doc_before_patch["id"]}',
        json={"data": {"title": "changed"}},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 200, result
    doc_after_patch = result["data"]

    assert doc_before_patch["title"] != doc_after_patch["title"]
    assert doc_before_patch["dateModified"] != doc_after_patch["dateModified"]

    resp = await api.get(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents/{doc_before_patch["id"]}',
    )
    assert resp.status == 200, result
    assert result["data"] == doc_after_patch

    resp = await api.get(f'/api/vendors/{vendor["data"]["id"]}')
    assert resp.status == 200, result
    assert result["data"]["dateModified"] == doc_after_patch["dateModified"]


async def test_vendor_ban_doc_invalid_signature(api, vendor, vendor_ban):
    doc_hash = "0" * 32
    valid_url = generate_test_url(doc_hash)
    parsed_url = urlparse(valid_url)
    parsed_query = dict(parse_qsl(parsed_url.query))
    parsed_query["Signature"] = "9WSTGSxvtKn%2FsNoKl5%2BpL%2By7z2Rh4%2FtJtHgWw4hqGHxgVK727KLuGUlytoammkWc3j9e" \
                                "RtOopaF1rgrUsaExDw%3D%3D"
    invalid_url = "{}?{}".format(valid_url.split("?")[0], urlencode(parsed_query))
    doc_data = {
        "title": "name.doc",
        "url": invalid_url,
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/vendors/{vendor["data"]["id"]}/bans/{vendor_ban["data"]["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Document url signature is invalid: data.__root__']} == result
