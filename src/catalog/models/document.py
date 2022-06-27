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

    @validator("id", always=True)
    def generate_id(cls, v, values, **kwargs):
        return uuid4().hex

    @root_validator
    def process_url(cls, values):
        validate_url_from_doc_service(values["url"])
        validate_url_signature(values["url"], values["hash"])
        values["url"] = build_api_document_url(values["id"], values["url"])
        return values


class DocumentPatchData(BaseModel):
    title: str = Field(..., min_length=1)


class Document(DocumentPostData):
    dateModified: datetime
    dateCreated: datetime


DocumentPostInput = AuthorizedInput[DocumentPostData]
DocumentPatchInput = AuthorizedInput[DocumentPatchData]
DocumentList = ListResponse[Document]
DocumentResponse = Response[Document]