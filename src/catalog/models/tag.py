from typing import Optional

from pydantic import Field, model_validator, ValidationError
from slugify import slugify

from catalog.models.api import Input, Response, ListResponse
from catalog.models.base import BaseModel


class PostTag(BaseModel):
    id: Optional[str] = Field(None, example="tag1")
    name: str
    name_en: str

    @model_validator(mode="before")
    def generate_id(cls, values):
        if values.get("id") and not values["id"].isalnum():
            raise ValidationError("must be alphanumeric")
        values["id"] = values.get("id") or slugify(values["name_en"])
        return values

    @property
    def active(self):
        return True


class PatchTag(BaseModel):
    name: Optional[str] = Field(None, example="Тег")
    name_en: Optional[str] = Field(None, example="Tag")
    active: Optional[bool] = Field(None, example=False)


class Tag(BaseModel):
    id: str
    name: str
    name_en: str
    active: bool


TagCreateInput = Input[PostTag]
TagUpdateInput = Input[PatchTag]
TagResponse = Response[Tag]
TagList = ListResponse[Tag]
