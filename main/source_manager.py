"""
Use this module to get "sourced" decorator, which will allow you to access data_stack elements without giving bot_id
"""

from functools import wraps
from collections import deque

_DATA_STACK = {}


class SourceManager:
    """
    Will return the "sourced" decorator
    """
    own_prosp = ('bot_id',)

    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        _DATA_STACK[self.bot_id] = deque()

    def append(self, **kwargs) -> dict:
        new_data = kwargs
        _DATA_STACK[self.bot_id].append(new_data)
        return new_data

    def pop(self) -> dict:
        return _DATA_STACK[self.bot_id].pop()

    @property
    def is_empty(self):
        return not _DATA_STACK[self.bot_id]

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __getattr__(self, item):
        if item == 'own_props' or item in self.own_prosp or item in self.__dict__:
            return self.__dict__[item]
        return _DATA_STACK[self.bot_id][-1][item]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __setattr__(self, key, value):
        if key in self.own_prosp or key in self.__dict__:
            self.__dict__[key] = value
        else:
            _DATA_STACK[self.bot_id][-1][key] = value

    def __iter__(self):
        return iter(_DATA_STACK[self.bot_id][-1].keys())

    def __str__(self):
        return str(_DATA_STACK[self.bot_id][-1])

    @property
    def sourced(self):
        """
        Will return the decorator
        """

        def decorator(func):
            @wraps(func)
            def inner(*args, from_args=False,
                      **kwargs):  # args are not used, will stay it here while integrating with commands
                return func(_DATA_STACK[self.bot_id][-1] if not from_args else kwargs)

            return inner

        return decorator

    def get(self, item):
        return _DATA_STACK[self.bot_id][-1].get(item)


if __name__ == '__main__':
    source_manager = SourceManager(1)
    source_manager.append(a='b')
    print(source_manager.a)
    print(list(source_manager))
