from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSerializer
from catalog.serializers.product import ProductSerializer


class ProductRequestSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
        "product": ProductSerializer,
    }

    def __init__(self, data: dict, **kwargs):
        super().__init__(data, **kwargs)
        if category := self.kwargs.get("category"):
            data["marketAdministrator"] = category.get("marketAdministrator")

        if contributor := self.kwargs.get("contributor"):
            data["contributor"] = contributor["contributor"]
            data["contributor"]["id"] = data.pop("contributor_id", None)
