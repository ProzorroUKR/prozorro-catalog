from random import randint
from copy import deepcopy
from unittest.mock import patch, AsyncMock
from urllib.parse import quote
from uuid import uuid4

from catalog.db import get_category_collection
from .base import TEST_AUTH, TEST_AUTH_NO_PERMISSION, TEST_AUTH_ANOTHER


async def create_blank_criterion(api, profile):
    profile_id = profile["data"]["id"]

    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria",
        json={
            "data": {
                "description": "Спосіб використання (одноразова або багаторазова)",
                "title": "Спосіб використання",
                "legislation": [{
                    "identifier": {
                        "id": "identifier_id",
                        "legalName": "legal_name",
                        "uri": "http://example.com",
                    },
                    "version": "1.0.0"
                }],
                "classification": {
                    "id": "classification_id",
                    "scheme": "scheme",
                }
            },
            "access": profile["access"]
        },
        auth=TEST_AUTH,
    )
    resp_json = await resp.json()
    criterion_id = resp_json["data"]["id"]
    assert resp_json["data"]["legislation"][0]["type"] == "NATIONAL_LEGISLATION"

    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criterion_id}/requirementGroups",
        json={
            "data": {"description": "Спосіб використання - одноразова",},
            "access": profile["access"]
        },
        auth=TEST_AUTH,
    )
    resp_json = await resp.json()
    rg_id = resp_json["data"]["id"]

    return criterion_id, rg_id


async def test_310_profile_create(api, category):
    category_id = category['data']['id']
    profile_id = '{}-{}'.format(randint(100000, 900000), category_id)

    profile = api.get_fixture_json('profile')
    profile['id'] = profile_id
    profile['relatedCategory'] = category_id
    test_profile = {
        "access": dict(category['access']),
        "data": profile,
    }

    resp = await api.get('/api/profiles/%s' % profile_id)
    assert resp.status == 404

    resp = await api.patch('/api/profiles/%s' % profile_id,
                           json=test_profile, auth=TEST_AUTH)
    assert resp.status == 404
    assert await resp.json() == {"errors": ["Profile not found"]}

    resp = await api.put('/api/profiles/%s' % profile_id + '-1', json=test_profile, auth=TEST_AUTH)
    assert resp.status == 400
    assert await resp.json() == {'errors': ['id mismatch']}

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile, auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403
    assert await resp.json() == {'errors': ["Forbidden 'profile' write operation"]}

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile, auth=TEST_AUTH_ANOTHER)
    assert resp.status == 403
    assert await resp.json() == {'errors': ['Owner mismatch']}

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile, auth=TEST_AUTH)
    assert resp.status == 201
    resp_json = await resp.json()
    assert resp_json['data']['id'] == test_profile['data']['id']
    assert 'access' in resp_json
    assert 'token' in resp_json['access']
    assert resp_json['data']['unit'] == category['data']['unit']
    assert resp_json['data']['classification'] == category['data']['classification']
    assert resp_json['data']['agreementID'] == category['data']['agreementID']
    assert resp_json['data']['dateCreated'] == resp_json['data']['dateModified']
    test_date_modified = resp_json['data']['dateModified']

    invalid_profile = deepcopy(test_profile)
    invalid_profile["data"]["additionalClassifications"] = [{
        "id": "test",
        "description": "test",
        "scheme": "ATC",
    }]

    with patch('catalog.validations.CachedSession.get') as medicine_resp:
        medicine_resp.return_value = AsyncMock()
        medicine_resp.return_value.__aenter__.return_value.status = 200
        medicine_resp.return_value.__aenter__.return_value.json.return_value = {"data": {"foo": "bar"}}
        resp = await api.put(f'/api/profiles/{profile_id}', json=invalid_profile, auth=TEST_AUTH)
        assert resp.status == 400
        assert {"errors": ["values {'test'} don't exist in ATC dictionary"]} == await resp.json()

        medicine_resp.return_value.__aenter__.return_value.status = 400
        resp = await api.put(f'/api/profiles/{profile_id}', json=invalid_profile, auth=TEST_AUTH)
        assert resp.status == 400
        assert {"errors": [
            "Can't get classification ATC from medicine registry, please make request later"
        ]} == await resp.json()

    # test data type
    for criteria in resp_json['data']["criteria"]:
        for r_group in criteria["requirementGroups"]:
            for requirement in r_group["requirements"]:
                if requirement["dataType"] == "integer":
                    # pq bot converts it to str and then it passed to api to be converted to int
                    assert type(requirement["minValue"]) is int
                elif requirement["dataType"] == "number":
                    assert type(requirement["minValue"]) is float

    test_profile_copy = deepcopy(test_profile)
    test_profile['access'] = resp_json['access']

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile_copy, auth=TEST_AUTH)
    assert resp.status == 400

    resp = await api.get('/api/profiles')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert profile_id in [i['id'] for i in resp_json['data']]

    resp = await api.get('/api/profiles/%s' % profile_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == test_profile['data']['id']
    assert resp_json['data']['dateModified'] == test_date_modified
    test_profile['data']['dateModified'] = test_date_modified

    await get_category_collection().find_one_and_update({"_id": category_id}, {"$unset": {"agreementID": ""}})
    profile_id = '{}-{}'.format(randint(100000, 900000), category_id)
    test_profile_copy["data"]["id"] = profile_id
    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile_copy, auth=TEST_AUTH)
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == ["Related category doesn't have agreementID"]


async def test_profile_post(api, category):
    category_id = category['data']['id']

    profile_id = '{}-{}'.format(randint(100000, 900000), category_id)

    profile = api.get_fixture_json('profile')
    profile['id'] = profile_id
    profile['relatedCategory'] = category_id
    test_profile = {
        "access": dict(category['access']),
        "data": profile,
    }

    resp = await api.post('/api/profiles', json=test_profile, auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403
    assert {'errors': ["Forbidden 'profile' write operation"]} == await resp.json()

    resp = await api.post('/api/profiles', json=test_profile, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['extra fields not permitted: data.id']} == await resp.json()

    test_profile["data"].pop("id", None)
    resp = await api.post('/api/profiles', json=test_profile, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    resp = await resp.json()
    assert 'access' in resp
    assert 'token' in resp['access']
    profile_id = resp['data']['id']

    resp = await api.get(f"/api/profiles/{profile_id}")
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == profile_id


async def test_311_profile_limit_offset(api, category):
    category_id = category['data']['id']

    profile = api.get_fixture_json('profile')

    # create 11 profiles
    profile_map = {}
    for i in range(11):
        profile_copy = deepcopy(profile)
        if i > 0:
            profile_copy['title'] += f" copy {i}"
        profile_id = '{}-{}'.format(randint(100000, 900000), category_id)
        profile_copy['id'] = profile_id
        profile_copy['relatedCategory'] = category_id

        resp = await api.put(f"/api/profiles/{profile_id}",
                             json={"data": profile_copy,
                                   "access": category['access']},
                             auth=TEST_AUTH)
        assert resp.status == 201, await resp.json()
        resp_json = await resp.json()
        assert resp_json['data']['id'] == profile_copy['id']
        assert 'access' in resp_json
        assert 'token' in resp_json['access']
        profile_map[profile_id] = resp_json['data']['dateModified']

    offset = ''
    pre_next_page = None
    for i in range(4):
        resp = await api.get(f"/api/profiles?limit=5&offset={quote(offset)}")
        assert resp.status == 200
        resp_json = await resp.json()

        if i == 3:
            assert len(resp_json['data']) == 0
            assert pre_next_page == resp_json['next_page']
            break
        pre_next_page = resp_json["next_page"]

        assert len(resp_json['data']) > 0
        assert len(resp_json['data']) <= 5
        assert 'next_page' in resp_json
        assert 'offset' in resp_json['next_page']
        offset = resp_json['next_page']['offset']
        prev = resp_json['data'][0]
        assert profile_map[prev['id']] == prev['dateModified']
        for item in resp_json['data'][1:]:
            assert prev['dateModified'] < item['dateModified']
            assert profile_map[item['id']] == item['dateModified']

    resp = await api.get('/api/profiles?reverse=1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    prev = resp_json['data'][0]
    assert profile_map.pop(prev['id']) == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert profile_map.pop(item['id']) == item['dateModified']

    assert len(profile_map) == 0


async def test_320_profile_patch(api, profile, category):
    profile_id = profile['data']['id']

    resp = await api.get(f'/api/profiles/{profile_id}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert profile_id == resp_json['data']['id']

    patch_profile_bad = {"data": {"id": "new-id"}}
    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile_bad)
    assert resp.status == 401, await resp.json()
    assert await resp.json(), {'errors': ['Authorization header not found']}

    patch_profile_bad = {"data": {"id": "new-id"}}
    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile_bad, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert await resp.json(), {'errors': ['Access token not found']}

    patch_profile_bad_token = {
        "data": {"title": "new title"},
        "access": {'token': "a" * 32},
    }
    resp = await api.patch(f'/api/profiles/{profile_id}',
                           json=patch_profile_bad_token,
                           auth=TEST_AUTH)
    assert resp.status == 403, await resp.json()

    patch_profile_bad['access'] = profile['access']

    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile_bad, auth=TEST_AUTH)
    assert resp.status == 400

    patch_profile = {
        "data": {
            "title": "Маска (прихована)",
            "status": "hidden"
        },
        "access": profile['access']
    }

    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_profile['data'].items():
        assert resp_json['data'][key] == patch_value

    test_date_modified = resp_json['data']['dateModified']
    assert test_date_modified > profile["data"]["dateModified"]
    assert test_date_modified > resp_json["data"]["dateCreated"]

    resp = await api.get(f'/api/profiles/{profile_id}')
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_profile['data'].items():
        assert resp_json['data'][key] == patch_value

    patch_profile["data"]["status"] = "active"
    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'active'

    patch_profile["data"] = {"agreementID": uuid4().hex}
    with patch('catalog.state.profile.validate_agreement', return_value=AsyncMock()) as mock_agreement:
        resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile, auth=TEST_AUTH)
        assert resp.status == 200
        resp_json = await resp.json()
        assert resp_json["data"]["agreementID"] != category["data"]["agreementID"]


async def test_330_requirement_create(api, category, profile_without_criteria):
    profile = profile_without_criteria
    profile_id = profile["data"]["id"]

    criteria_id, rg_id = await create_blank_criterion(api, profile)
    requirement_data = {
        "access": profile["access"],
        "data": {
            "title": "Три шари або більше",
            "dataType": "string",
            "expectedMinItems": 3,
        }
    }

    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
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
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
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
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems couldn't be greater then expectedMaxItems: data.__root__"
    ]

    requirement_data["data"]["expectedMaxItems"] = 6
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMaxItems couldn't be greater then count of items in expectedValues: data.__root__"
    ]

    requirement_data["data"]["expectedMinItems"] = 5
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems couldn't be greater then count of items in expectedValues: data.__root__"
    ]

    del requirement_data["data"]["expectedMinItems"]
    del requirement_data["data"]["expectedMaxItems"]
    requirement_data["data"]["expectedValue"] = "someValue"

    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValue couldn't exists together with one of ['minValue', 'maxValue', 'expectedValues']: data.__root__"
    ]

    del requirement_data["data"]["expectedValues"]
    requirement_data["data"]["maxValue"] = ""
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValue couldn't exists together with one of ['minValue', 'maxValue', 'expectedValues']: data.__root__"
    ]

    del requirement_data["data"]["expectedValue"]
    requirement_data["data"]["expectedValues"] = ["value1", "value2", "value3", "value4"]
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValues couldn't exists together with one of ['minValue', 'maxValue', 'expectedValue']: data.__root__"
    ]

    del requirement_data["data"]["maxValue"]
    requirement_data["data"]["title"] = "Тест allOf_1"
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    resp_json = await resp.json()
    assert "expectedMinItems" not in resp_json["data"][0]
    assert "expectedMaxItems" not in resp_json["data"][0]
    assert "expectedValue" not in resp_json["data"][0]
    assert "minValue" not in resp_json["data"][0]
    assert "maxValue" not in resp_json["data"][0]
    assert "expectedValues" in resp_json["data"][0]

    requirement_data["data"]["expectedMinItems"] = 1
    requirement_data["data"]["expectedMaxItems"] = 3
    requirement_data["data"]["title"] = "Тест allOf_2"
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    resp_json = await resp.json()
    assert "isArchived" not in resp_json["data"][0]
    assert "expectedMinItems" in resp_json["data"][0]
    assert "expectedMaxItems" in resp_json["data"][0]
    assert "expectedValues" in resp_json["data"][0]
    assert resp_json["data"][0]["title"] == "Тест allOf_2"

    category_id = category["data"]["id"]
    c_criteria_id = category["data"]["criteria"][0]["id"]
    c_rg_id = category["data"]["criteria"][0]["requirementGroups"][0]["id"]
    c_req_id = category["data"]["criteria"][0]["requirementGroups"][0]["requirements"][0]["id"]
    resp = await api.patch(
        f"/api/categories/{category_id}/criteria/{c_criteria_id}/requirementGroups/{c_rg_id}/requirements/{c_req_id}",
        json={"data": {"isArchived": True}, "access": category["access"]},
        auth=TEST_AUTH,
    )

    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["data"]["isArchived"] is True

    requirement_data["data"]["title"] = "Одноразова"
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        f"requirement '{requirement_data['data']['title']}' is archived"
    ]

    requirement_data["data"]["title"] = "Не існуючий"
    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        f"requirement '{requirement_data['data']['title']}' not found in category {category['data']['id']}"
    ]


async def test_331_requirement_patch(api, profile_without_criteria):
    profile = profile_without_criteria
    access = profile["access"]
    profile_id = profile["data"]["id"]
    criteria_id, rg_id = await create_blank_criterion(api, profile)
    requirement_data = {
        "access": profile["access"],
        "data": {
            "title": "Одноразова",
            "dataType": "string",
            "expectedValues": ["value1", "value2", "value3", "value4"],
        }
    }

    resp = await api.post(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements",
        json=requirement_data,
        auth=TEST_AUTH,
    )

    # assert resp.status == 201
    resp_json = await resp.json()
    requirement_id = resp_json["data"][0]["id"]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 3, "expectedValues": []}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems and expectedMaxItems couldn't exist without expectedValues: __root__"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 5}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems couldn't be greater then count of items in expectedValues: __root__"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMaxItems": 5}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMaxItems couldn't be greater then count of items in expectedValues: __root__"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 6, "expectedMaxItems": 5}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedMinItems couldn't be greater then expectedMaxItems: __root__"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedValue": "value"}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValue couldn't exists together with one of ['minValue', 'maxValue', 'expectedValues']: __root__"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"minValue": "value"}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "expectedValues couldn't exists together with one of ['minValue', 'maxValue', 'expectedValue']: __root__"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 0}, "access": access},
        auth=TEST_AUTH,
    )
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json["errors"] == [
        "ensure this value is greater than 0: data.expectedMinItems"
    ]

    resp = await api.patch(
        f"/api/profiles/{profile_id}/criteria/{criteria_id}/requirementGroups/{rg_id}/requirements/{requirement_id}",
        json={"data": {"expectedMinItems": 3}, "access": profile["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["data"]["expectedMinItems"] == 3
    assert set(resp_json["data"]["expectedValues"]) == set(requirement_data["data"]["expectedValues"])
