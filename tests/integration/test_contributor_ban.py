from catalog.doc_service import generate_test_url
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

    data = api.get_fixture_json('ban')
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
