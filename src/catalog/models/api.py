from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

DataT = TypeVar('DataT')


class Access(BaseModel):
    token: str = Field(..., regex=r"[0-9a-f]{32}")


class Error(BaseModel):
    code: int
    message: str


class Input(GenericModel, Generic[DataT]):
    data: DataT
    access: Optional[Access]


class Response(GenericModel, Generic[DataT]):
    data: Optional[DataT]
    errors: Optional[List[Error]]


class ErrorResponse(BaseModel):
    errors: List[Error]


class PaginatedList(BaseModel):
    data: Any
    next_page: Optional[dict]

