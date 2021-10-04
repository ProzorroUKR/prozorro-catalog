from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

DataT = TypeVar('DataT')


class Access(BaseModel):
    token: str = Field(..., regex=r"[0-9a-f]{32}")


class Input(GenericModel, Generic[DataT]):
    data: DataT
    access: Optional[Access]


class Response(GenericModel, Generic[DataT]):
    data: Optional[DataT]
    errors: Optional[List[str]]


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
