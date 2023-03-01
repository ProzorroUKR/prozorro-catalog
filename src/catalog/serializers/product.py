from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSerializer


class ProductSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }

    def __init__(self, data, vendor=None, show_owner=True):
        super().__init__(data, show_owner)
        if vendor and 'vendor' in data:
            data['vendor'].update({
                'name': vendor['vendor']['name'],
                'identifier': vendor['vendor']['identifier'],
            })

        if data.get("relatedProfiles"):
            data["relatedProfile"] = data["relatedProfiles"][0]
