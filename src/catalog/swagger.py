from pydantic.schema import schema
from types import MethodType
from catalog import models
import os.path


class class_view_swagger_path(object):

    def __init__(self, swagger_path):
        assert os.path.isdir(swagger_path), \
            "Should be a directory with get.yaml, post.yaml, etc."
        self.swagger_path = swagger_path

    def __call__(self, decorated):
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
    for name in dir(models):
        obj = getattr(models, name)
        if hasattr(obj, "schema"):
            model_classes.append(obj)
    generated_schema = schema(
        model_classes,
        ref_prefix='#/components/schemas/'
    )
    return generated_schema["definitions"]
