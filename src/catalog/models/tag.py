from typing import Optional, List
from uuid import uuid4

from pydantic import Field, model_validator, ValidationError, field_validator
from slugify import slugify

from catalog.models.api import Input, Response, ListResponse
from catalog.models.base import BaseModel


class PostTag(BaseModel):
    code: Optional[str] = Field(None, example="tag1")
    name: str
    name_en: str

    @model_validator(mode="before")
    def generate_code(cls, values):
        if values.get("code") and not values["code"].isalnum():
            raise ValidationError("must be alphanumeric")
        values["code"] = values.get("code") or slugify(values["name_en"])
        return values

    @property
    def id(self):
        return uuid4().hex


class PatchTag(BaseModel):
    name: Optional[str] = Field(None, example="Тег")
    name_en: Optional[str] = Field(None, example="Tag")


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
        if len(tags) != len(set(tags)):
            raise ValueError("Tags must be unique")
        return tags


TagCreateInput = Input[PostTag]
TagUpdateInput = Input[PatchTag]
TagResponse = Response[Tag]
TagList = ListResponse[Tag]
