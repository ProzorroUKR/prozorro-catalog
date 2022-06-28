

class BaseState:

    @classmethod
    def on_post(cls, data):
        cls.always(data)

    @classmethod
    def on_patch(cls, before, after):
        cls.always(after)

    @classmethod
    def always(cls, data):  # post or patch
        pass
