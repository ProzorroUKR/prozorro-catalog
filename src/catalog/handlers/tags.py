import logging
from copy import deepcopy
from typing import Optional, Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.context import get_final_session_time
from catalog.models.api import ErrorResponse
from catalog.models.common import SuccessResponse
from catalog.models.tag import TagList, TagResponse, TagCreateInput, TagUpdateInput
from catalog.auth import validate_accreditation
from catalog.serializers.tag import TagSerializer
from catalog.utils import get_revision_changes

logger = logging.getLogger(__name__)


class TagView(PydanticView):
    async def get(self, /, limit: Optional[int] = 100, active: Optional[bool] = None) -> r200[TagList]:
        """
        Get a list of tags

        Tags: Tags
        """
        tags = await db.find_tags(limit=limit, active=active)
        return {"data": [TagSerializer(tag).data for tag in tags]}

    async def post(
        self, /, body: TagCreateInput
    ) -> Union[r201[TagResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create tag

        Security: Basic: []
        Tags: Tags
        """
        validate_accreditation(self.request, "category")

        # export data back to dict
        data = body.data.dict_without_none()
        get_revision_changes(self.request, new_obj=data)

        await db.insert_tag(data)

        logger.info(
            f"Created tag {data['id']}",
            extra={
                "MESSAGE_ID": "tag_create_post",
                "tag_id": data['id'],
                "session": get_final_session_time(),
            },
        )
        return {"data": TagSerializer(data).data}


class TagItemView(PydanticView):

    async def get(self, tag_id: str, /) -> Union[r200[TagResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get tag

        Tags: Tags
        """
        tag = await db.read_tag(tag_id)
        return {"data": TagSerializer(tag).data}

    async def patch(
        self, tag_id: str, /, body: TagUpdateInput
    ) -> Union[r200[TagResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Tag update

        Security: Basic: []
        Tags: Tags
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_tag(tag_id) as tag:
            # export data back to dict
            data = body.data.dict_without_none()
            old_tag = deepcopy(tag)
            tag.update(data)
            get_revision_changes(self.request, new_obj=tag, old_obj=old_tag)

            logger.info(
                f"Updated tag {tag_id}",
                extra={"MESSAGE_ID": "tag_patch", "session": get_final_session_time()},
            )

        return {"data": TagSerializer(tag).data}

    async def delete(self, tag_id: str, /) -> Union[r200[SuccessResponse], r404[ErrorResponse]]:
        """
        Tag delete

        Security: Basic: []
        Tags: Tags
        """
        validate_accreditation(self.request, "category")
        await db.find_objects_with_tag(tag_id)
        await db.delete_tag(tag_id)
        return {"result": "success"}
