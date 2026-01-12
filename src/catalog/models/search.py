from enum import Enum
from typing import Set, Union

from pydantic import BaseModel, Field

from catalog.models.api import Input
from catalog.models.category import Category
from catalog.models.product import Product
from catalog.models.profile import Profile


class ResourceType(str, Enum):
    category = "category"
    profile = "profile"
    product = "product"
    offer = "offer"


class SearchData(BaseModel):
    resource: ResourceType
    ids: Set[str] = Field(..., min_length=1, max_length=300)


SearchInput = Input[SearchData]


class SearchResponse(BaseModel):
    data: Union[Category, Profile, Product]
