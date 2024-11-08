
def evaluate_serializer(serializer, value, obj=None):
    kwargs = {}
    if obj:
        kwargs = obj.kwargs
    if type(serializer).__name__ == "function":
        value = serializer(obj, value, **kwargs)
    else:
        value = serializer(value, **kwargs).data
    return value


class ListSerializer:
    def __init__(self, serializer, **kwargs):
        self.kwargs = kwargs
        self.serializer = serializer

    def __call__(self, data, **kwargs):
        self._data = data
        self.kwargs.update(kwargs)
        return self

    @property
    def data(self) -> list:
        if self._data:
            return [evaluate_serializer(self.serializer, e, self) for e in self._data]


class BaseSerializer:
    _data: dict
    serializers = {}
    calculated = {}
    private_fields = None
    whitelist = None

    def __init__(self, data: dict, **kwargs):
        self.kwargs = kwargs
        self._data = data

    def get_raw(self, k):
        return self._data.get(k)

    @property
    def data(self) -> dict:
        items = ((k, v) for k, v in self._data.items())
        if self.private_fields:
            items = ((k, v)
                     for k, v in items
                     if k not in self.private_fields)
        if self.whitelist:
            items = ((k, v)
                     for k, v in items
                     if k in self.whitelist)

        data = {
            k: self.serialize_value(k, v)
            for k, v in items
        }
        for k, v in self.calculated.items():
            value = v(data)
            if value is not None:
                data[k] = v(data)
        return data

    def serialize_value(self, key, value):
        serializer = self.serializers.get(key)
        if serializer:
            value = evaluate_serializer(serializer, value, self)
        return value


class RootSerializer(BaseSerializer):
    def __init__(self, data: dict, **kwargs):
        access = data.pop("access", None)
        show_owner = kwargs.get("show_owner", True)

        if access and show_owner:
            data["owner"] = access["owner"]
        super().__init__(data, **kwargs)
