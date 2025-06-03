from .base import TEST_AUTH
from urllib.parse import urlparse, parse_qsl, urlencode
from catalog.doc_service import generate_test_url, get_doc_service_uid_from_url


async def test_vendor_product_doc_create(api, vendor, vendor_product):
    vendor, access = vendor["data"], vendor["access"]
    product = vendor_product["data"]
    req_path = f'/api/vendors/{vendor["id"]}/products/{product["id"]}/documents'
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        req_path,
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
        f"/api/vendors/{vendor['id']}/products/{product['id']}/documents/{data['id']}?download={ds_uid}"
    assert expected == data["url"]

    resp = await api.patch(
        f'{req_path}/{data["id"]}',
        json={
            "data": {"title": "Updated title"},
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 200, result
    assert result["data"]["title"] == "Updated title"


async def test_vendor_product_doc_invalid_signature(api, vendor, vendor_product):
    vendor, access = vendor["data"], vendor["access"]
    product = vendor_product["data"]
    req_path = f'/api/vendors/{vendor["id"]}/products/{product["id"]}/documents'

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
        req_path,
        json={
            "data": doc_data,
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Value error, document url signature is invalid: data']} == result
