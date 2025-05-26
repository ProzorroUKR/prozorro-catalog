from pydantic import BaseModel, schema_json_of
from types import MethodType
from catalog import models
from catalog.settings import SWAGGER_DOC_AVAILABLE
import os.path


class class_view_swagger_path(object):

    def __init__(self, swagger_path):
        if SWAGGER_DOC_AVAILABLE:
            assert os.path.isdir(swagger_path), \
                "Should be a directory with get.yaml, post.yaml, etc."
            self.swagger_path = swagger_path

    def __call__(self, decorated):
        if SWAGGER_DOC_AVAILABLE:
            for name in os.listdir(self.swagger_path):
                if name.endswith(".yaml"):
                    full_name = os.path.join(self.swagger_path, name)
                    handler = getattr(decorated, name[:-5], None)
                    if handler is not None:
                        # cannot assign attribute to a method
                        if isinstance(handler, MethodType):
                            handler = handler.__func__
                        setattr(handler, "swagger_file", full_name)
        return decorated


def get_definitions():
    model_classes = []
    for module in dir(models):
        if module and not module.startswith("__"):
            sub_module = getattr(models, module)
            for obj_name in dir(sub_module):
                if not obj_name.startswith("__"):
                    obj = getattr(sub_module, obj_name)
                    if isinstance(obj, type) and issubclass(obj, BaseModel):
                        model_classes.append(obj)

    generated_schema = schema_json_of(
        model_classes,
        ref_prefix='#/components/schemas/'
    )
    return generated_schema["definitions"]
