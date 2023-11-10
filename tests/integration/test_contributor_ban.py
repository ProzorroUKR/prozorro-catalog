from copy import deepcopy
from datetime import timedelta

from aiohttp import BasicAuth
from freezegun import freeze_time

from catalog.doc_service import generate_test_url
from catalog.utils import get_now
from .base import TEST_AUTH


async def test_create_ban_by_not_market_administrator(api, contributor):
    data = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    data['documents'][0]['url'] = generate_test_url(doc_hash)
    data['documents'][0]['hash'] = f"md5:{doc_hash}"
    data['administrator']['identifier']['id'] = '12121212'
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of market administrators: data.administrator.identifier']} == result


async def test_create_ban_permission(api, contributor):
    data = api.get_fixture_json('ban')
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=BasicAuth(login="boo"),
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'category' write operation"]} == result


async def test_ban_create_invalid_fields(api, contributor):
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": {}},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    errors = [
        'field required: data.reason',
        'field required: data.description',
        'field required: data.administrator',
    ]
    assert {'errors': errors} == result

    data = deepcopy(api.get_fixture_json('ban'))
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Can add document only from document service: data.documents.0.__root__']} == result

    data['documents'][0]['url'] = generate_test_url(data["documents"][0]["hash"])
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Document url signature is invalid: data.documents.0.__root__']} == result

    del data["documents"]
    data["reason"] = "some other reason"
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of market/ban_reason.json keys: data.reason']} == result

    data["reason"] = "rulesViolation"
    data["description"] = "test"
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must equal Порушення правил роботи в каталозі: data.description']} == result

    data = deepcopy(api.get_fixture_json('ban'))
    data["dueDate"] = (get_now() - timedelta(days=1)).isoformat()
    del data["documents"]
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/bans",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['should be greater than now: data.dueDate']} == result


async def test_ban_create(api, contributor):
    contributor = contributor["data"]
    test_ban = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    test_ban['documents'][0]['url'] = generate_test_url(doc_hash)
    test_ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result
    assert "data" in result
    data = result["data"]
    assert "owner" in result["data"]

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in test_ban}
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'owner'}

    # create ban without dueDate
    del test_ban["dueDate"]
    test_ban["administrator"]["identifier"]["id"] = "40996564"
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    # check quantity of bans in contributor object
    resp = await api.get(f'/api/crowd-sourcing/contributors/{contributor["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]["bans"]) == 2


async def test_ban_get(api, contributor, ban):
    contributor = contributor["data"]
    ban = ban["data"]
    resp = await api.get(f'/api/crowd-sourcing/contributors/{contributor["id"]}/bans/{ban["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {
        'id', 'reason', 'owner', 'dateCreated', 'description', 'administrator', 'documents', 'dueDate'
    }


async def test_bans_list(api, contributor, ban):
    contributor = contributor["data"]
    resp = await api.get(f'/api/crowd-sourcing/contributors/{contributor["id"]}/bans')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]) == 1
    assert set(result["data"][0].keys()) == {
        'id', 'reason', 'owner', 'dateCreated', 'description', 'administrator', 'documents', 'dueDate'
    }
    assert result["data"][0]["id"] == ban["data"]["id"]


async def test_ban_already_exists(api, contributor):
    # create ban from administrator 42574629 with dueDate
    contributor = contributor["data"]
    test_ban = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    test_ban['documents'][0]['url'] = generate_test_url(doc_hash)
    test_ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    test_ban["dueDate"] = (get_now() + timedelta(days=1)).isoformat()
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    # add new ban from administrator 42574629 before dueDate
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['ban from this market administrator already exists']} == result

    # add new ban from administrator 42574629 after dueDate
    del test_ban["dueDate"]
    with freeze_time((get_now() + timedelta(days=2)).isoformat()):
        resp = await api.post(
            f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
            json={"data": test_ban},
            auth=TEST_AUTH,
        )
        result = await resp.json()
        assert resp.status == 201, result

    # create ban from administrator 40996564 without dueDate
    test_ban = api.get_fixture_json('ban')
    doc_hash = "0" * 32
    test_ban['documents'][0]['url'] = generate_test_url(doc_hash)
    test_ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    del test_ban["dueDate"]
    test_ban["administrator"]["identifier"]["id"] = "40996564"
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    # add new ban from administrator 40996564 before dueDate
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": test_ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['ban from this market administrator already exists']} == result
