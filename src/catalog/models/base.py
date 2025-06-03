from pydantic import BaseModel as PydanticBaseModel


unchanged = object()


class PropertySerializationModel(PydanticBaseModel):

    def dict(self, *args,  include=None, exclude=None, **kwargs):
        result = super().dict(*args, include=include,  exclude=exclude, **kwargs)
        cls = self.__class__
        props = [
            prop for prop in dir(cls)
            if isinstance(getattr(cls, prop), property)
            and prop not in ("__values__", "fields", "model_extra", "__fields_set__", "model_fields_set")  # excluding pydantic properties
        ]
        # Include and exclude properties
        if include:
            props = [prop for prop in props if prop in include]
        if exclude:
            props = [prop for prop in props if prop not in exclude]

        # Update the attribute dict with the properties
        if props:
            result.update({prop: getattr(self, prop) for prop in props})
        return result


class BaseModel(PropertySerializationModel):
    class Config:
        validate_assignment = True
        use_enum_values = True
        extra = "forbid"

    def dict_without_none(self, include=None, exclude=None):
        data = self.dict(
            include=include,
            exclude=exclude,
            by_alias=True,
            exclude_none=True,
        )
        return data

