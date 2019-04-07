if __name__ == '__main__':  # Setting up django for testing
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'TelegramProblemGenerator.settings')
    django.setup()

from types import MappingProxyType

from main import command_handlers
from os import path, listdir
import importlib

"""
Getting mapping of the names and modules of the command_handler
{'answer': <function ...>, 'send': <function ...>, ...}
Using MappingProxyType to prevent the dict from being modified.

Just import COMMANDS_MAPPING from this module.
"""

COMMANDS_MAPPING = MappingProxyType(
    {fn: getattr(importlib.import_module('.{mn}'.format(mn=fn), 'main.command_handlers'), fn) for fn in
     (path.splitext(pt)[0] for pt in listdir(command_handlers.__path__[0])) if
     fn[:2] != '__'})

if __name__ == '__main__':
    print(COMMANDS_MAPPING)
