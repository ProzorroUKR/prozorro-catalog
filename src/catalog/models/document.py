from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator, root_validator
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse, AuthorizedInput, ListResponse
from catalog.doc_service import validate_url_from_doc_service, validate_url_signature, build_api_document_url
from uuid import uuid4


class DocumentPostData(BaseModel):
    id: str = None
    hash: str = Field(..., regex=r"^md5:[0-9a-f]{32}$")
    title: str = Field(..., min_length=1)
    format: str
    url: str
    description: Optional[str]

    @validator("id", always=True)
    def generate_id(cls, v, values, **kwargs):
        return uuid4().hex

    @root_validator
    def process_url(cls, values):
        if 'url' in values and 'hash' in values:
            validate_url_from_doc_service(values["url"])
            validate_url_signature(values["url"], values["hash"])
            values["url"] = build_api_document_url(values["id"], values["url"])
        return values


class DocumentPutData(DocumentPostData):
    @validator("id", always=True)
    def generate_id(cls, v, values, **kwargs):
        return v or uuid4().hex


class DocumentPatchData(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str]


class Document(DocumentPostData):
    dateModified: datetime
    datePublished: datetime


class PublishedDocument(DocumentPostData):
    datePublished: datetime


class DocumentSign(BaseModel):
    hash: str
    title: str
    format: str
    url: str


DocumentPostInput = AuthorizedInput[DocumentPostData]
DocumentPutInput = AuthorizedInput[DocumentPutData]
DocumentPatchInput = AuthorizedInput[DocumentPatchData]
DocumentList = ListResponse[Document]
DocumentResponse = Response[Document]
DocumentSignResponse = Response[DocumentSign]
