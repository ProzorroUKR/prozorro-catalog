from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError
from urllib.parse import urlparse, parse_qsl, unquote, urlencode
from uuid import uuid4
from time import time
from base64 import b64encode, b64decode
from catalog.context import get_request
from .settings import (
    DOC_SERVICE_SIGNING_SEED,
    DOC_SERVICE_SEEDS,
    DOC_SERVICE_KEY_LENGTH,
    DOC_SERVICE_URL,
    DOC_SERVICE_DEP_URL,
)


URL_DOC_KEY = "documents"

signer = SigningKey(DOC_SERVICE_SIGNING_SEED, encoder=HexEncoder)
signer_keyid = signer.verify_key.encode(encoder=HexEncoder)[:8].decode()

verifiers_keyring = {
    key[:DOC_SERVICE_KEY_LENGTH].decode(): VerifyKey(key, encoder=HexEncoder)
    for key in DOC_SERVICE_SEEDS
}


def validate_url_from_doc_service(url):
    if not url.startswith(DOC_SERVICE_URL):
        if not DOC_SERVICE_DEP_URL or not url.startswith(DOC_SERVICE_DEP_URL):
            raise ValueError("can add document only from document service")

    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split("/")
    if len(path_parts) != 3:
        raise ValueError("document service url has an unexpected path")

    parsed_query = dict(parse_qsl(parsed_url.query))
    if {"Signature", "KeyID"} != set(parsed_query):
        raise ValueError("document service url has unexpected query params")


def validate_url_signature(url, doc_hash):
    parsed_url = urlparse(url)
    parsed_query = dict(parse_qsl(parsed_url.query))

    # get verifier
    keyid = parsed_query["KeyID"]
    if keyid not in verifiers_keyring:
        raise ValueError("Signed by an unknown key")  # "Document url expired" in CDB
    verifier = verifiers_keyring[keyid]

    # get the signature
    signature = parsed_query["Signature"]
    try:
        signature = b64decode(unquote(signature))
    except Exception:
        raise ValueError("document url signature has an unexpected format")

    # compose the expected message
    doc_hash = doc_hash.split(":")[-1]
    path_parts = parsed_url.path.split("/")
    doc_uuid = path_parts[-1]
    message = f"{doc_uuid}\0{doc_hash}".encode()

    # validate signature
    try:
        verifier.verify(message, signature)
    except BadSignatureError:
        raise ValueError("document url signature is invalid")


def generate_test_url(doc_hash):
    doc_uid = uuid4().hex
    verifier = signer.verify_key
    # Important: do not call this function
    verifiers_keyring[verifier.encode(encoder=HexEncoder)[:8].decode()] = verifier

    keyid = verifier.encode(encoder=HexEncoder)[:8].decode()
    msg = f"{doc_uid}\0{doc_hash}".encode()
    signature = b64encode(signer.sign(msg).signature)
    query = {"Signature": signature, "KeyID": keyid}
    return "{}/get/{}?{}".format(DOC_SERVICE_URL, doc_uid, urlencode(query))


def build_api_document_url(api_uid, doc_service_url):
    r = get_request()
    doc_service_uid = get_doc_service_uid_from_url(doc_service_url)
    doc_path = r.path
    if URL_DOC_KEY in doc_path:
        doc_path = doc_path[:doc_path.find(URL_DOC_KEY)+len(URL_DOC_KEY)]
    return f"{doc_path}/{api_uid}?download={doc_service_uid}"


def get_doc_service_uid_from_url(url):
    parsed_url = urlparse(url)
    doc_service_uid = parsed_url.path.split("/")[-1]
    return doc_service_uid


def get_ds_id_from_api_url(doc):
    doc_url = urlparse(doc["url"])
    doc_service_uid = dict(parse_qsl(doc_url.query)).get("download")
    return doc_service_uid


def get_doc_download_url(ds_id, temporary=True):
    query = {"KeyID": signer_keyid}
    if temporary:
        expires = int(time()) + 300  # EXPIRES
        mess = f"{ds_id}\0{expires}"
        query["Expires"] = expires
    else:
        mess = ds_id
    query["Signature"] = b64encode(signer.sign(mess.encode()).signature)
    return f"{DOC_SERVICE_URL}/get/{ds_id}?{urlencode(query)}"



