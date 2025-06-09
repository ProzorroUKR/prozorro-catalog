from .base import TEST_AUTH, TEST_AUTH_NO_PERMISSION
from .conftest import db


async def test_tag_create_no_permission(api):
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег", "name_en": "test tag"}},
        auth=TEST_AUTH_NO_PERMISSION,
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'category' write operation"]} == result


async def test_tag_create(db, api, mock_agreement):
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег", "name_en": "test tag"}},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    assert "data" in result
    data = result["data"]
    assert data["code"] == "test-tag"
    assert "id" not in data
    assert data["name"] == "тест тег"
    assert data["name_en"] == "test tag"

    # try to create tag with the same name
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег", "name_en": "test tag 1"}},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["Duplicate value for 'name': 'тест тег'"]}

    # try to create tag with the same name_en
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег 1", "name_en": "test tag", "code": "test-tag-1"}},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["Duplicate value for 'name_en': 'test tag'"]}

    # try to create tag with the same code
    resp = await api.post(
        '/api/tags',
        json={"data": {"code": "test-tag", "name": "тест тег 1", "name_en": "test tag 1"}},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["Duplicate value for 'code': 'test-tag'"]}

    # try to create new unique tag with the code
    resp = await api.post(
        '/api/tags',
        json={"data": {"code": "test-tag-1", "name": "тест тег 1", "name_en": "test tag 1"}},
        auth=TEST_AUTH,
    )

    result = await resp.json()

    assert resp.status == 201, result

    assert "data" in result
    data = result["data"]
    assert data["code"] == "test-tag-1"
    assert "id" not in data
    assert data["name"] == "тест тег 1"
    assert data["name_en"] == "test tag 1"


async def test_tag_patch(db, api):
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег", "name_en": "test tag"}},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    resp = await api.patch(
        '/api/tags/test-tag',
        json={"data": {"name": "Новий тег"}},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    result = await resp.json()
    assert result["data"]["name"] == "Новий тег"

    # create second tag
    resp = await api.post(
        '/api/tags',
        json={"data": {"code": "test-tag-1", "name": "тест тег 1", "name_en": "test tag 1"}},
        auth=TEST_AUTH,
    )

    assert resp.status == 201, result

    # try to patch name for duplicated one
    resp = await api.patch(
        '/api/tags/test-tag-1',
        json={"data": {"name": "Новий тег"}},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["Duplicate value for 'name': 'Новий тег'"]}

    # try to patch code
    resp = await api.patch(
        '/api/tags/test-tag-1',
        json={"data": {"code": "new"}},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ['Extra inputs are not permitted: data.code']}


async def test_tag_get(api, tag):
    resp = await api.get(f'/api/tags/new')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'code', 'name', 'name_en'}

    resp = await api.get(f'/api/tags/new-tag')
    assert resp.status == 404


async def test_tag_list(db, api):
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег", "name_en": "test tag"}},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег 1", "name_en": "test tag 1"}},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    resp = await api.get(f'/api/tags')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]) == 2
    for tag in result["data"]:
        assert "id" not in tag


async def test_tag_delete(db, api, category):
    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег", "name_en": "test tag"}},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    resp = await api.post(
        '/api/tags',
        json={"data": {"name": "тест тег 1", "name_en": "test tag 1"}},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    resp = await api.get(f'/api/tags')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]) == 2
    for tag in result["data"]:
        assert "id" not in tag


    resp = await api.delete(
        '/api/tags/test-tag',
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 200
    assert result["result"] == "success"

    resp = await api.get(f'/api/tags')
    assert resp.status == 200
    result = await resp.json()
    assert len(result["data"]) == 1

    # try to delete non existed one
    resp = await api.delete(
        '/api/tags/foo',
        auth=TEST_AUTH,
    )
    assert resp.status == 404

    # try to delete tag that is used in category
    category_id = category["data"]['id']
    resp = await api.patch(
        f'/api/categories/{category_id}',
        json={"data": {"tags": ["test-tag-1"]}, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 200

    resp = await api.delete(
        '/api/tags/test-tag-1',
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["Tag `test-tag-1` is used in categories ['33190000-0000-42574629']"]}
