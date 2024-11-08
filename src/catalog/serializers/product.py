from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSerializer


def set_field_from_requirements(criteria, requirement_responses):
    requirements = {
        req["title"]: {**req, "classification": c.get("classification")}
        for c in criteria
        for rg in c.get("requirementGroups", "")
        for req in rg.get("requirements", "")
    }

    fields_to_copy = ("classification", "unit")

    for rr in requirement_responses:
        req = requirements.get(rr["requirement"])
        if not req:
            return

        for field in fields_to_copy:
            if req.get(field):
                rr[field] = req[field]


class ProductSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }

    def __init__(
            self,
            data: dict,
            **kwargs,

    ):
        super().__init__(data, **kwargs)
        vendor = self.kwargs.get("vendor")
        category = self.kwargs.get("category")
        if vendor and 'vendor' in data:
            data['vendor'].update({
                'name': vendor['vendor']['name'],
                'identifier': vendor['vendor']['identifier'],
            })

        if category:
            set_field_from_requirements(
                category.get("criteria", ""),
                data.get("requirementResponses", "")
            )
