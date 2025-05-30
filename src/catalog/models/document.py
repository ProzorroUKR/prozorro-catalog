from datetime import datetime
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse, AuthorizedInput, ListResponse
from catalog.doc_service import validate_url_from_doc_service, validate_url_signature, build_api_document_url
from uuid import uuid4


class DocumentPostData(BaseModel):
    id: Optional[str] = Field(None, example=uuid4().hex)
    hash: str = Field(..., pattern=r"^md5:[0-9a-f]{32}$")
    title: str = Field(..., min_length=1)
    format: str
    url: str
    description: Optional[str] = Field(None, example="description")

    @model_validator(mode="before")
    def process_url(cls, values):
        if "id" not in values:
            values["id"] = uuid4().hex
        if 'url' in values and 'hash' in values:
            validate_url_from_doc_service(values["url"])
            validate_url_signature(values["url"], values["hash"])
            values["url"] = build_api_document_url(values["id"], values["url"])
        return values


class DocumentPutData(DocumentPostData):
    @field_validator("id")
    def generate_id(cls, v, values, **kwargs):
        return v or uuid4().hex


class DocumentPatchData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, example="title")
    description: Optional[str] = Field(None, example="description")


class Document(DocumentPostData):
    dateModified: datetime
    datePublished: datetime


DOCUMENT_EXAMPLE = {
    "id": uuid4().hex,
    "title": "name.doc",
    "url": "/documents/name.doc",
    "hash": f"md5:{uuid4().hex}",
    "format": "application/msword",
    "dateModified": datetime.now().isoformat(),
    "datePublished": datetime.now().isoformat(),
}

class DocumentSign(BaseModel):
    hash: str
    title: str
    format: str
    url: str


DocumentPostInput = AuthorizedInput[DocumentPostData]
DocumentPutInput = AuthorizedInput[DocumentPutData]
DocumentPatchInput = AuthorizedInput[DocumentPatchData]
DocumentNonAuthorizedInputPost = Input[DocumentPostData]
DocumentNonAuthorizedInputPatch = Input[DocumentPatchData]
DocumentList = ListResponse[Document]
DocumentResponse = Response[Document]
DocumentSignResponse = Response[DocumentSign]
