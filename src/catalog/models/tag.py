from typing import Optional, List
from uuid import uuid4

from pydantic import Field, model_validator, field_validator
from slugify import slugify

from catalog.models.api import Input, Response, ListResponse
from catalog.models.base import BaseModel


class PostTag(BaseModel):
    code: Optional[str] = Field(None, min_length=1, example="tag1")
    name: str = Field(..., min_length=1)
    name_en: str = Field(..., min_length=1)

    @field_validator("name", "name_en", "code", mode="before")
    @classmethod
    def not_empty_or_whitespace(cls, v: str) -> str:
        return v.strip() if v is not None else v

    @model_validator(mode="before")
    def generate_code(cls, values):
        if values.get("code") and not values["code"].replace("-", "").isalnum():
            raise ValueError("`code` must be alphanumeric")
        values["code"] = values.get("code") or slugify(values.get("name_en", ""))
        return values

    @property
    def id(self):
        return uuid4().hex


class PatchTag(BaseModel):
    name: Optional[str] = Field(None, min_length=1, example="Тег")
    name_en: Optional[str] = Field(None, min_length=1, example="Tag")

    @field_validator("name", "name_en",  mode="before")
    @classmethod
    def not_empty_or_whitespace(cls, v: str) -> str:
        return v.strip() if v is not None else v


class Tag(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    code: str
    name: str
    name_en: str


class TagsMixin:
    tags: Optional[List[str]] = Field(None, example=["tag1", "tag2"])

    @field_validator("tags")
    @classmethod
    def tags_must_be_unique(cls, tags: List[str]):
        if tags and len(tags) != len(set(tags)):
            raise ValueError("tags must be unique")
        return tags


TagCreateInput = Input[PostTag]
TagUpdateInput = Input[PatchTag]
TagResponse = Response[Tag]
TagList = ListResponse[Tag]
