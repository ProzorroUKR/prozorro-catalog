from aiohttp.web_urldispatcher import View
from catalog.state.base import BaseState


class BaseView(View):
    state_class = BaseState
    state: BaseState

