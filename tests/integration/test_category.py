from copy import deepcopy
from random import randint
from urllib.parse import quote
from .base import TEST_AUTH_NO_PERMISSION, TEST_AUTH, TEST_AUTH_ANOTHER
from .conftest import set_requirements_to_responses
from .utils import create_profile, create_criteria


async def test_110_category_create(api, mock_agreement):
    test_category = api.get_fixture_json('category')

    resp = await api.put('/api/categories/123', auth=TEST_AUTH)
    assert resp.status == 400

    resp = await api.put('/api/categories', json=test_category, auth=TEST_AUTH)
    assert resp.status == 405

    category_id = '{}-{}-{}'.format(
        test_category['classification']['id'][:8],
        randint(1000, 9999),
        test_category['marketAdministrator']['identifier']['id']
    )
    test_category['id'] = category_id

    resp = await api.put('/api/categories/%s' % category_id + '-1',
                         json=test_category,
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['field required: data']} == await resp.json()

    resp = await api.put('/api/categories/%s' % category_id + '-1',
                         json={"data": test_category},
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['id mismatch']} == await resp.json()

    test_category['id'] = category_id[:18]

    resp = await api.put('/api/categories/%s' % category_id[:18],
                         json={"data": test_category},
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['string does not match regex "^[0-9A-Za-z_-]{20,32}$": data.id']} == await resp.json()

    test_category['id'] = category_id

    resp = await api.put(f"/api/categories/{category_id}",
                         json=test_category,
                         auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403
    assert {'errors': ["Forbidden 'category' write operation"]} == await resp.json()

    invalid_data = deepcopy(test_category)
    invalid_data["additionalClassifications"][0]["id"] = "test"
    invalid_data["additionalClassifications"][0]["scheme"] = "INN"
    resp = await api.put(
        f'/api/categories/{category_id}',
        json={"data": invalid_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    assert {"errors": ["values {'test'} don't exist in INN dictionary"]} == await resp.json()


    resp = await api.put(f'/api/categories/{category_id}',
                         json={"data": test_category},
                         auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    resp_json = await resp.json()
    assert 'access' in resp_json
    assert 'token' in resp_json['access']

    test_category['access'] = dict(resp_json['access'])
    test_date_modified = resp_json['data']['dateModified']

    resp = await api.get('/api/categories')
    assert resp.status == 200
    resp_json = await resp.json()
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert category_id in [i['id'] for i in resp_json['data']]
    items = [i for i in resp_json['data'] if i['id'] == category_id]
    assert len(items) == 1
    assert items[0]['dateModified'] == test_date_modified
    test_category['dateModified'] = test_date_modified

    resp = await api.get('/api/categories/..')
    assert resp.status == 404

    resp = await api.get('/api/categories/../../../../../../../../../../etc/passwd')
    assert resp.status == 404

    resp = await api.get('/api/categories/%s-bad' % category_id)
    assert resp.status == 404

    resp = await api.get('/api/categories/%s' % category_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == category_id


async def test_category_post(api, mock_agreement):
    test_category = deepcopy(api.get_fixture_json('category'))

    resp = await api.post('/api/categories', json={"data": test_category}, auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403
    assert {'errors': ["Forbidden 'category' write operation"]} == await resp.json()

    resp = await api.post('/api/categories', json={"data": test_category}, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['extra fields not permitted: data.id']} == await resp.json()

    test_category.pop("id", None)
    resp = await api.post('/api/categories', json={"data": test_category}, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    category_data = await resp.json()
    assert 'access' in category_data
    assert 'token' in category_data['access']
    category_id = category_data['data']['id']

    resp = await api.get(f"/api/categories/{category_id}")
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == category_id

    # create product for this category with new md5 id format
    category = await create_criteria(api, "categories", category_data)
    test_product = {"data": deepcopy(api.get_fixture_json('product'))}
    test_product["data"]["relatedCategory"] = category_id
    set_requirements_to_responses(test_product["data"]["requirementResponses"], category)
    test_product['access'] = category_data['access']

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()

    # create profile for this category with new md5 id format
    profile = deepcopy(api.get_fixture_json('profile'))
    profile['relatedCategory'] = category_id
    test_profile = {
        "access": dict(category['access']),
        "data": profile,
    }

    resp = await api.post('/api/profiles', json=test_profile, auth=TEST_AUTH)
    assert resp.status == 201
    resp_json = await resp.json()
    assert 'id' in resp_json['data']
    assert 'access' in resp_json
    assert 'token' in resp_json['access']


async def test_111_limit_offset(api, mock_agreement):
    test_category = api.get_fixture_json('category')
    test_category_map = dict()

    for i in range(11):
        test_category_copy = deepcopy(test_category)
        test_category_copy['title'] += " copy {}".format(i + 1)
        category_id = '{}-{}-{}'.format(
            test_category['classification']['id'][:8],
            randint(1000, 9999),
            test_category['marketAdministrator']['identifier']['id']
        )
        test_category_copy['id'] = category_id
        resp = await api.put(f'/api/categories/{category_id}',
                             json={"data": test_category_copy},
                             auth=TEST_AUTH)
        assert resp.status == 201
        resp_json = await resp.json()
        assert 'access' in resp_json
        assert 'token' in resp_json['access']
        test_category_map[category_id] = resp_json['data']['dateModified']

    # check for empty limit
    resp = await api.get('/api/categories')
    assert resp.status == 200, await resp.json()
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0

    # check for negative limit
    resp = await api.get('/api/categories?limit=-1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0

    # first page forward
    resp = await api.get('/api/categories?limit=5')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 5
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] < item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_normal = resp_json['next_page']['offset']

    # first page backward
    resp = await api.get('/api/categories?limit=8&reverse=1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 8
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_reverse = resp_json['next_page']['offset']

    assert offset_normal != offset_reverse

    # second page fowrard
    resp = await api.get('/api/categories?limit=10&offset=' + quote(offset_normal))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 6  # 11 total, first page 5, second 6
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] < item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    prev_resp_json = resp_json
    offset_normal = resp_json['next_page']['offset']

    # third page forward (must be empty)
    resp = await api.get('/api/categories?limit=10&offset=' + quote(offset_normal))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 0
    assert prev_resp_json['next_page'] == resp_json['next_page']

    # second page backward
    resp = await api.get('/api/categories?limit=8&reverse=1&offset=' + quote(offset_reverse))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 3  # 11 total, 8 on first, 3 on second
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_reverse = resp_json['next_page']['offset']

    # third page backward (must be empty)
    resp = await api.get('/api/categories?limit=8&reverse=1&offset=' + quote(offset_reverse))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 0

    # invalid offset
    offset = "1729285200.000000"
    resp = await api.get(f'/api/categories?limit=8&reverse=1&offset={offset}')
    assert resp.status == 400, resp.json()
    result = await resp.json()
    assert {'errors': [f'Invalid offset: {offset}']} == result

    offset = "2024-08-20T10:03:07.108768+03:00"
    resp = await api.get(f'/api/categories?limit=8&reverse=1&offset={offset}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 0


async def test_120_category_patch(api, category):
    category_id = category["data"]['id']
    patch_category_bad = {
        "data": {
            "marketAdministrator": {
                "address": {
                    "countryName": "Україна",
                    "locality": "Київ",
                    "postalCode": "02200",
                    "region": "Київ",
                    "streetAddress": "вулиця Ушинського, 40"
                }
            }
        }
    }

    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category_bad)
    assert resp.status == 401
    assert await resp.json() == {'errors': ['Authorization header not found']}

    patch_category_bad['access'] = {'token': 'bad token value, but long enough'}

    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category_bad,
                           auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403, await resp.json()

    patch_category_bad['access'] = category['access']

    resp = await api.patch('/api/categories/%s' % category_id,
                           json={"data": {}, "access": category['access']},
                           auth=TEST_AUTH_ANOTHER)
    assert resp.status == 403, await resp.json()
    assert {'errors': ['Owner mismatch']} == await resp.json()

    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category_bad,
                           auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()

    patch_category = {
        "data": {
            "title": "Респіратори та маски без клапану (приховані)",
            "status": "hidden"
        }
    }
    resp = await api.patch('/api/categories/%s' % category_id, json=patch_category,
                           headers={'X-Access-Token': category['access']['token']},
                           auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_category['data'].items():
        assert resp_json['data'][key] == patch_value

    test_date_modified = resp_json['data']['dateModified']
    assert test_date_modified > category["data"]["dateModified"]

    resp = await api.get('/api/categories')
    assert resp.status == 200
    resp_json = await resp.json()
    items = [i for i in resp_json['data'] if i['id'] == category_id]
    assert len(items) == 1
    assert items[0]['dateModified'] == test_date_modified

    patch_category['access'] = category['access']

    resp = await api.get('/api/categories/%s' % category_id)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_category['data'].items():
        assert resp_json['data'][key] == patch_value

    patch_category["data"]["status"] = "active"
    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category,
                           auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'active'


async def test_130_requirement_create(api, category):
    category_id = category["data"]["id"]
    criteria_id = category["data"]["criteria"][0]["id"]
    rg_id = category["data"]["criteria"][0]["requirementGroups"][0]["id"]
    requirement_data = {
        "access": category["access"],
        "data": {
            "title": "Requirement with expectedValues",
            "dataType": "string",
        }
    }

    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValues is required when dataType string: data.__root__"
    ]

    requirement_data["data"]["expectedValues"] = []
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "ensure this value has at least 1 items: data.expectedValues",
        "expectedMinItems is required when expectedValues exists and should be equal 1: data.__root__"
    ]

    requirement_data["data"]["expectedMinItems"] = 3
    del requirement_data["data"]["expectedValues"]
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems and expectedMaxItems couldn't exist without expectedValues: data.__root__"
    ]

    requirement_data["data"]["expectedMaxItems"] = 2

    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems and expectedMaxItems couldn't exist without expectedValues: data.__root__"
    ]

    requirement_data["data"]["expectedValues"] = ["value1", "value2", "value3", "value4"]

    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems is required when expectedValues exists and should be equal 1: data.__root__"
    ]

    requirement_data["data"]["expectedMinItems"] = 1
    requirement_data["data"]["expectedMaxItems"] = 6
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
         "expectedMaxItems should be equal 1 or not exist at all: data.__root__"
    ]

    requirement_data["data"]["expectedMaxItems"] = 1
    requirement_data["data"]["unit"] = {
        "code": "H87",
        "name": "штуки"
    }

    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "Unit is forbid with dataType: string: data.__root__",
    ]

    del requirement_data["data"]["expectedMinItems"]
    del requirement_data["data"]["expectedMaxItems"]
    del requirement_data["data"]["expectedValues"]
    del requirement_data["data"]["unit"]

    requirement_data["data"]["expectedValue"] = "someValue"

    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "value is not a valid boolean: data.expectedValue",
        "value is not a valid integer: data.expectedValue",
        "value is not a valid float: data.expectedValue",
        "expectedValues is required when dataType string: data.__root__",
    ]

    requirement_data["data"]["expectedValue"] = 4
    requirement_data["data"]["dataType"] = "integer"
    requirement_data["data"]["maxValue"] = ""
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "value is not a valid integer: data.maxValue",
        "value is not a valid float: data.maxValue",
    ]

    requirement_data["data"]["maxValue"] = 2
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValue couldn't exists together with one of ['minValue', 'maxValue', 'expectedValues']: data.__root__"
    ]

    # try to create integer characteristic without minValue/expectedValue
    del requirement_data["data"]["expectedValue"]
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "minValue is required when dataType number or integer: data.__root__"
    ]

    requirement_data["data"]["minValue"] = 1
    requirement_data["data"]["expectedValues"] = [2, 3]
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "str type expected: data.expectedValues.0",
        "str type expected: data.expectedValues.1",
        "expectedMinItems is required when expectedValues exists and should be equal 1: data.__root__"
    ]

    requirement_data["data"]["expectedValues"] = ["value1", "value2", "value3", "value4"]
    requirement_data["data"]["expectedMinItems"] = 1
    requirement_data["data"]["dataType"] = "string"
    del requirement_data["data"]["minValue"]
    del requirement_data["data"]["maxValue"]
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    resp_json = await resp.json()
    assert "isArchived" in resp_json["data"][0]
    assert resp_json["data"][0]["isArchived"] is False
    assert "expectedMinItems" in resp_json["data"][0]
    assert "expectedMaxItems" not in resp_json["data"][0]
    assert "expectedValue" not in resp_json["data"][0]
    assert "minValue" not in resp_json["data"][0]
    assert "maxValue" not in resp_json["data"][0]
    assert "expectedValues" in resp_json["data"][0]

    requirement_data["data"]["expectedMinItems"] = 1
    requirement_data["data"]["expectedMaxItems"] = 1
    requirement_data["data"]["title"] = "Requirement with expectedValues 2"
    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    resp_json = await resp.json()
    assert "expectedMinItems" in resp_json["data"][0]
    assert "expectedMaxItems" in resp_json["data"][0]
    assert "expectedValues" in resp_json["data"][0]


async def test_131_requirement_patch(api, category):
    access = category["access"]
    category_id = category["data"]["id"]
    criteria_id = category["data"]["criteria"][0]["id"]
    rg_id = category["data"]["criteria"][0]["requirementGroups"][0]["id"]
    requirement_data = {
        "access": category["access"],
        "data": {
            "title": "Requirement with expectedValues",
            "dataType": "string",
            "expectedMinItems": 1,
            "expectedValues": ["value1", "value2", "value3", "value4"],
        }
    }

    resp = await api.post(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )

    assert resp.status == 201
    resp_json = await resp.json()
    requirement_id = resp_json["data"][0]["id"]

    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 3, "expectedValues": None}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems and expectedMaxItems couldn't exist without expectedValues: __root__"
    ]

    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 5}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems is required when expectedValues exists and should be equal 1: __root__"
    ]

    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMaxItems": 5}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMaxItems should be equal 1 or not exist at all: __root__"
    ]

    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={
            "data": {
                "expectedValue": 5,
                "dataType": "integer",
                "expectedValues": None,
                "expectedMinItems": None,
                "expectedMaxItems": None,
                "minValue": 0,
            },
            "access": access,
        },
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValue couldn't exists together with one of ['minValue', 'maxValue', 'expectedValues']: __root__"
    ]

    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 0}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "ensure this value is greater than 0: data.expectedMinItems"
    ]

    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMaxItems": 1}, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["data"]["expectedMaxItems"] == 1
    assert set(resp_json["data"]["expectedValues"]) == set(requirement_data["data"]["expectedValues"])


async def test_140_category_agreement_id_patch(api, category):
    category_id = category["data"]['id']

    agreement_id = "2" * 32
    patch_category = {
        "access": category["access"],
        "data": {
            "agreementID": "2"*32
        }
    }

    profile_1 = await create_profile(api, category)
    profile_2 = await create_profile(api, category, {"status": "general"})
    profile_3 = await create_profile(api, category, {"status": "hidden"})

    resp = await api.patch(f'/api/categories/{category_id}',
                           json=patch_category,
                           auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['agreementID'] == agreement_id

    resp = await api.get(f'/api/profiles/{profile_1["data"]["id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['agreementID'] == agreement_id

    resp = await api.get(f'/api/profiles/{profile_2["data"]["id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['agreementID'] == agreement_id

    resp = await api.get(f'/api/profiles/{profile_3["data"]["id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['agreementID'] == agreement_id
