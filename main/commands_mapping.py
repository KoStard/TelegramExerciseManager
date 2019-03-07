from types import MappingProxyType
from main import command_handlers
from main.command_handlers import *
from os import path

"""
Getting mapping of the names and modules of the command_handler
{'answer': <function ...>, 'send': <function ...>, ...}
Using MappingProxyType to prevent the dict from being modified.

Just import COMMANDS_MAPPING from this module. 
"""



COMMANDS_MAPPING = MappingProxyType(
    {path.splitext(fn)[0]: getattr(globals()[path.splitext(fn)[0]], path.splitext(fn)[0]) for fn in
     command_handlers.__loader__.contents() if
     fn[:2] != '__'})

if __name__ == '__main__':
    print(COMMANDS_MAPPING)
