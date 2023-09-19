from .base import TEST_AUTH
from urllib.parse import urlparse, parse_qsl, urlencode
from catalog.doc_service import generate_test_url, get_doc_service_uid_from_url


async def test_contributor_doc_create(api, contributor):
    contributor, access = contributor["data"], contributor["access"]
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents',
        json={
            "data": doc_data,
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    data = result["data"]
    ds_uid = get_doc_service_uid_from_url(doc_data["url"])
    expected = f"{api.server.scheme}://{api.server.host}:{api.server.port}" \
        f"/api/crowd-sourcing/contributors/{contributor['id']}/documents/{data['id']}?download={ds_uid}"
    assert expected == data["url"]


async def test_contributor_doc_put(api, contributor, contributor_document):
    contributor, access = contributor["data"],  contributor["access"]
    doc_before_put = contributor_document["data"]

    doc_hash = "1" * 32
    doc_data = {
        "title": "name1.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.put(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents/{doc_before_put["id"]}',
        json={
            "data": doc_data,
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    doc_after_put = result["data"]
    assert doc_before_put["dateModified"] != doc_after_put["dateModified"]
    assert doc_before_put["url"].split("?")[0] == doc_after_put["url"].split("?")[0]
    assert doc_before_put["url"] != doc_after_put["url"]
    assert doc_before_put["datePublished"] == doc_after_put["datePublished"]
    assert doc_after_put["url"].split("/")[-2] == "documents"

    resp = await api.get(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents/{doc_before_put["id"]}',
    )
    assert resp.status == 200, result
    assert result["data"] == doc_after_put


async def test_contributor_doc_patch(api, contributor, contributor_document):
    contributor, access = contributor["data"], contributor["access"]
    doc_before_patch = contributor_document["data"]

    resp = await api.patch(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents/{doc_before_patch["id"]}',
        json={
            "data": {"title": "changed"},
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 200, result
    doc_after_patch = result["data"]

    assert doc_before_patch["title"] != doc_after_patch["title"]
    assert doc_before_patch["dateModified"] != doc_after_patch["dateModified"]

    resp = await api.get(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents/{doc_before_patch["id"]}',
    )
    assert resp.status == 200, result
    assert result["data"] == doc_after_patch


async def test_contributor_doc_invalid_signature(api, contributor):
    contributor, access = contributor["data"], contributor["access"]

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
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents',
        json={
            "data": doc_data,
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Document url signature is invalid: data.__root__']} == result
