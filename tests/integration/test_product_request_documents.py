# from copy import deepcopy
#
# from .base import TEST_AUTH
# from urllib.parse import urlparse, parse_qsl, urlencode
# from catalog.doc_service import generate_test_url, get_doc_service_uid_from_url
# from .test_product_request import request_review_data
# from .utils import get_fixture_json
# from .conftest import set_requirements_to_responses
#
#
# async def test_create_product_request_with_doc(api, contributor, category):
#     contributor = contributor["data"]
#     test_request = get_fixture_json('product_request')
#     category_id = category['data']['id']
#     set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
#     test_request["product"]['relatedCategory'] = category_id
#     doc_hash = "0" * 32
#     doc_data = {
#         "title": "name.doc",
#         "url": generate_test_url(doc_hash),
#         "hash": f"md5:{doc_hash}",
#         "format": "application/msword",
#     }
#     test_request["documents"] = [doc_data]
#
#     resp = await api.post(
#         f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
#         json={"data": test_request},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 201, result
#     product_request = result["data"]
#     document_data = product_request["documents"][0]
#     ds_uid = get_doc_service_uid_from_url(doc_data["url"])
#     expected = f"{api.server.scheme}://{api.server.host}:{api.server.port}" \
#         f"/api/crowd-sourcing/requests/{product_request['id']}/documents/{document_data['id']}?download={ds_uid}"
#     assert expected == document_data["url"]
#
#     resp = await api.get(f'/api/crowd-sourcing/requests/{product_request["id"]}')
#     assert resp.status == 200, result
#     assert result["data"]["dateModified"] == document_data["dateModified"]
#
#
# async def test_product_request_doc_create(api, product_request):
#     product_request = product_request["data"]
#     doc_hash = "0" * 32
#     doc_data = {
#         "title": "name.doc",
#         "url": generate_test_url(doc_hash),
#         "hash": f"md5:{doc_hash}",
#         "format": "application/msword",
#     }
#     resp = await api.post(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents',
#         json={"data": doc_data},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 201, result
#     data = result["data"]
#     ds_uid = get_doc_service_uid_from_url(doc_data["url"])
#     expected = f"{api.server.scheme}://{api.server.host}:{api.server.port}" \
#         f"/api/crowd-sourcing/requests/{product_request['id']}/documents/{data['id']}?download={ds_uid}"
#     assert expected == data["url"]
#
#     resp = await api.get(f'/api/crowd-sourcing/requests/{product_request["id"]}')
#     assert resp.status == 200, result
#     assert result["data"]["dateModified"] == data["dateModified"]
#
#
# async def test_product_request_doc_create_for_reviewed_product_request(api, product_request):
#     product_request = product_request["data"]
#     resp = await api.post(
#         f"api/crowd-sourcing/requests/{product_request['id']}/accept",
#         json={"data": request_review_data},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 201, result
#
#     doc_hash = "0" * 32
#     doc_data = {
#         "title": "name.doc",
#         "url": generate_test_url(doc_hash),
#         "hash": f"md5:{doc_hash}",
#         "format": "application/msword",
#     }
#     resp = await api.post(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents',
#         json={"data": doc_data},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 403, result
#     assert {'errors': ['Forbidden to add/update document for product request that has been reviewed']} == result
#
#
# async def test_product_request_doc_put(api, product_request, product_request_document):
#     product_request = product_request["data"]
#     doc_before_put = product_request_document["data"]
#
#     doc_hash = "1" * 32
#     doc_data = {
#         "title": "name1.doc",
#         "url": generate_test_url(doc_hash),
#         "hash": f"md5:{doc_hash}",
#         "format": "application/msword",
#     }
#     resp = await api.put(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents/{doc_before_put["id"]}',
#         json={"data": doc_data},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 201, result
#     doc_after_put = result["data"]
#     assert doc_before_put["dateModified"] != doc_after_put["dateModified"]
#     assert doc_before_put["url"].split("?")[0] == doc_after_put["url"].split("?")[0]
#     assert doc_before_put["url"] != doc_after_put["url"]
#     assert doc_before_put["datePublished"] != doc_after_put["datePublished"]
#     assert doc_after_put["url"].split("/")[-2] == "documents"
#
#     resp = await api.get(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents/{doc_before_put["id"]}',
#     )
#     assert resp.status == 200, result
#     assert result["data"] == doc_after_put
#
#     resp = await api.get(f'/api/crowd-sourcing/requests/{product_request["id"]}')
#     assert resp.status == 200, result
#     assert result["data"]["dateModified"] == doc_after_put["dateModified"]
#
#
# async def test_product_request_doc_patch(api, product_request, product_request_document):
#     product_request = product_request["data"]
#     doc_before_patch = product_request_document["data"]
#
#     resp = await api.patch(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents/{doc_before_patch["id"]}',
#         json={"data": {"title": "changed"}},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 200, result
#     doc_after_patch = result["data"]
#
#     assert doc_before_patch["title"] != doc_after_patch["title"]
#     assert doc_before_patch["dateModified"] != doc_after_patch["dateModified"]
#
#     resp = await api.get(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents/{doc_before_patch["id"]}',
#     )
#     assert resp.status == 200, result
#     assert result["data"] == doc_after_patch
#
#     resp = await api.get(f'/api/crowd-sourcing/requests/{product_request["id"]}')
#     assert resp.status == 200, result
#     assert result["data"]["dateModified"] == doc_after_patch["dateModified"]
#
#
# async def test_product_request_doc_patch_for_reviewed_product_request(api, product_request, product_request_document):
#     product_request = product_request["data"]
#     doc_before_patch = product_request_document["data"]
#     rejection_data = deepcopy(request_review_data)
#     rejection_data.update({
#         "reason": ["invalidTitle", "alreadyAvailable"],
#         "description": "Невірно зазначена назва товару",
#     })
#     resp = await api.post(
#         f"api/crowd-sourcing/requests/{product_request['id']}/reject",
#         json={"data": rejection_data},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 201, result
#
#     resp = await api.patch(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents/{doc_before_patch["id"]}',
#         json={"data": {"title": "changed"}},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 403, result
#     assert {'errors': ['Forbidden to add/update document for product request that has been reviewed']} == result
#
#
# async def test_product_request_doc_invalid_signature(api, product_request):
#     product_request = product_request["data"]
#
#     doc_hash = "0" * 32
#     valid_url = generate_test_url(doc_hash)
#     parsed_url = urlparse(valid_url)
#     parsed_query = dict(parse_qsl(parsed_url.query))
#     parsed_query["Signature"] = "9WSTGSxvtKn%2FsNoKl5%2BpL%2By7z2Rh4%2FtJtHgWw4hqGHxgVK727KLuGUlytoammkWc3j9e" \
#                                 "RtOopaF1rgrUsaExDw%3D%3D"
#     invalid_url = "{}?{}".format(valid_url.split("?")[0], urlencode(parsed_query))
#     doc_data = {
#         "title": "name.doc",
#         "url": invalid_url,
#         "hash": f"md5:{doc_hash}",
#         "format": "application/msword",
#     }
#     resp = await api.post(
#         f'/api/crowd-sourcing/requests/{product_request["id"]}/documents',
#         json={"data": doc_data},
#         auth=TEST_AUTH,
#     )
#     result = await resp.json()
#     assert resp.status == 400, result
#     assert {'errors': ['Value error, document url signature is invalid: data']} == result
