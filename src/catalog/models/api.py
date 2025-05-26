from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

DataT = TypeVar('DataT')


class Access(BaseModel):
    token: str = Field(..., pattern=r"[0-9a-f]{32}")


class AccessOwner(Access):
    owner: str


class Input(BaseModel, Generic[DataT]):
    data: DataT


class AuthorizedInput(BaseModel, Generic[DataT]):
    data: DataT
    access: Optional[Access] = Field(None, example={"token": "11111111111111111111111111111111"})  # will be checked later cos we want 401 not 400


class BulkInput(BaseModel, Generic[DataT]):
    data: List[DataT]
    access: Optional[Access] = Field(None, example={"token": "11111111111111111111111111111111"})


class CreateResponse(BaseModel, Generic[DataT]):
    data: DataT
    access: AccessOwner


class Response(BaseModel, Generic[DataT]):
    data: DataT


class ListResponse(BaseModel, Generic[DataT]):
    data: List[DataT]


class ErrorResponse(BaseModel):
    errors: List[str]


class ListItem(BaseModel):
    id: str
    dateModified: str


class PageLink(BaseModel):
    offset: str
    path: str
    uri: str


class PaginatedList(BaseModel):
    data: List[ListItem]
    next_page: PageLink
    prev_page: Optional[PageLink]


AnyInput = Input[Any]
