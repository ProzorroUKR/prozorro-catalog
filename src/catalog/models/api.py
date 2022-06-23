from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

DataT = TypeVar('DataT')


class Access(BaseModel):
    token: str = Field(..., regex=r"[0-9a-f]{32}")


class AccessOwner(Access):
    owner: str


class Input(GenericModel, Generic[DataT]):
    data: DataT


class AuthorizedInput(GenericModel, Generic[DataT]):
    data: DataT
    access: Optional[Access]  # will be checked later cos we want 401 not 400


class BulkInput(GenericModel, Generic[DataT]):
    data: List[DataT]
    access: Optional[Access]


class CreateResponse(GenericModel, Generic[DataT]):
    data: DataT
    access: AccessOwner


class Response(GenericModel, Generic[DataT]):
    data: DataT


class ListResponse(GenericModel, Generic[DataT]):
    data: List[DataT]


class ErrorResponse(BaseModel):
    errors: List[str]


class ListItem(BaseModel):
    id: str
    dateModified: str


class NextPage(BaseModel):
    offset: str


class PaginatedList(BaseModel):
    data: List[ListItem]
    next_page: Optional[NextPage]


AnyInput = Input[Any]
