from catalog.models.api import Input, Response
from catalog.models.category import Category
from catalog.models.profile import Profile
from catalog.models.product import Product
from catalog.models.offer import Offer
from pydantic import BaseModel, Field
from typing import Set, Union
from enum import Enum


class ResourceType(str, Enum):
    category = "category"
    profile = "profile"
    product = "product"
    offer = "offer"


class SearchData(BaseModel):
    resource: ResourceType
    ids: Set[str] = Field(..., min_items=1, max_items=300)


SearchInput = Input[SearchData]


class SearchResponse(BaseModel):
    data: Union[Category, Profile, Product]
