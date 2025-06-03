from aiohttp import BasicAuth

from .base import TEST_AUTH


async def test_contributor_create_no_authorization(api):
    test_contributor = api.get_fixture_json('contributor')
    resp = await api.post(
        '/api/crowd-sourcing/contributors',
        json={"data": test_contributor},
    )
    result = await resp.json()
    assert resp.status == 401, result
    assert {'errors': ['Authorization header not found']} == result


async def test_contributor_create_permission(api):
    test_contributor = api.get_fixture_json('contributor')
    resp = await api.post(
        f"/api/crowd-sourcing/contributors",
        json={"data": test_contributor},
        auth=BasicAuth(login="boo"),
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'contributors' write operation"]} == result


async def test_contributor_email_validation(api):
    data = api.get_fixture_json('contributor')
    data['contributor']["contactPoint"].pop("email")
    resp = await api.post(
        "/api/crowd-sourcing/contributors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Field required: data.contributor.contactPoint.email']} == result

    invalid_values = ("", "123", 10, True, "foobar.com", "test@test")
    for value in invalid_values:
        data['contributor']["contactPoint"]["email"] = value
        resp = await api.post(
            "/api/crowd-sourcing/contributors",
            json={"data": data},
            auth=TEST_AUTH,
        )
        result = await resp.json()
        assert resp.status == 400, result
        error_msgs = [
            'Input should be a valid string: data.contributor.contactPoint.email',
            'value is not a valid email address: An email address must have an @-sign.: data.contributor.contactPoint.email',
            'value is not a valid email address: The part after the @-sign is not valid. It should have a period.: data.contributor.contactPoint.email',
        ]
        assert result["errors"][0] in error_msgs

    valid_values = (
        "Abc@example.tld",
        "user+mailbox/department=shipping@example.tld",
        "!#$%&'*+-/=?^_`.{|}~@example.tld",
        "jeff@臺網中心.tw",
    )
    for idx, value in enumerate(valid_values):
        data["contributor"]["contactPoint"]["email"] = value
        data["contributor"]["identifier"]["id"] = data["contributor"]["identifier"]["id"] + f"{idx}"
        resp = await api.post(
            "/api/crowd-sourcing/contributors",
            json={"data": data},
            auth=TEST_AUTH,
        )
        result = await resp.json()
        assert resp.status == 201, result


async def test_contributor_without_region(api):
    data = api.get_fixture_json('contributor')
    # 1
    data['contributor']["address"].pop("region")
    data['contributor']["address"]["countryName"] = "Україна"
    resp = await api.post(
        "/api/crowd-sourcing/contributors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Value error, region is required for countryName Україна: data.contributor.address']} == result

    # 2
    data['contributor']["address"]["countryName"] = "Антарктика"
    resp = await api.post(
        "/api/crowd-sourcing/contributors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result


async def test_contributor_ukrainian_region_dictionary(api, category):
    data = api.get_fixture_json('contributor')
    data['contributor']["address"] = {
      "countryName": "Україна",
      "region": "невідомий"
    }
    resp = await api.post(
        f"/api/crowd-sourcing/contributors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Value error, must be one of classifiers/ua_regions.json: data.contributor.address.region']} == result


async def test_contributor_create(api):
    test_contributor = api.get_fixture_json('contributor')
    resp = await api.post(
        '/api/crowd-sourcing/contributors',
        json={"data": test_contributor},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result

    assert "data" in result
    data = result["data"]

    # check passed data
    for k, v in test_contributor.items():
        assert data[k] == v

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in test_contributor}
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'dateModified', 'owner'}


async def test_contributor_duplicate(api):
    data = api.get_fixture_json('contributor')
    resp = await api.post(
        "/api/crowd-sourcing/contributors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    contributor = result["data"]

    # try create second contributor with the same identifier
    resp = await api.post(
        '/api/crowd-sourcing/contributors',
        json={"data": data},
        auth=TEST_AUTH,
    )
    result_duplicate = await resp.json()
    assert resp.status == 400, result_duplicate
    identifier_id = data["contributor"]["identifier"]["id"]
    expected = {
        'errors': [f'Cannot create contributor.identifier.id {identifier_id} already exists: {contributor["id"]}']
    }
    assert expected == result_duplicate


async def test_contributor_get(api, contributor):
    contributor = contributor["data"]
    resp = await api.get(f'/api/crowd-sourcing/contributors/{contributor["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'id', 'contributor', 'owner', 'dateCreated', 'dateModified'}


async def test_contributor_list(api, contributor):
    contributor = contributor["data"]
    resp = await api.get('/api/crowd-sourcing/contributors')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data', 'next_page'}
    assert len(result["data"]) == 1
    assert set(result["data"][0].keys()) == {'dateModified', 'id'}
    assert result["data"][0]["id"] == contributor["id"]


async def test_create_contributor_with_invalid_identifier(api):
    test_contributor = api.get_fixture_json('contributor')
    test_contributor['contributor']['identifier']['scheme'] = 'SOME_CODE'
    resp = await api.post(
        '/api/crowd-sourcing/contributors',
        json={"data": test_contributor},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': [
        'Value error, must be one of organizations/identifier_scheme.json codes: data.contributor.identifier.scheme'
    ]} == result
