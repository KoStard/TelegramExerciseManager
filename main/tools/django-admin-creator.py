import sys
import requests
from django.core.files import File
from datetime import datetime
import django
import sys
import os
import json

sys.path.append(
    "E:/Programming/Python/Django/Telegram Problem Controller/TelegramProblemGenerator/"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "TelegramProblemGenerator.settings")

django.setup()

res = """from django.contrib import admin\n"""
model_admin_template_with_fields =\
"""@admin.register({ModelName})
class {ModelName}Admin(admin.ModelAdmin):
    list_display=({fields})\n\n\n"""
model_admin_template_without_fields =\
"""@admin.register({ModelName})
class {ModelName}Admin(admin.ModelAdmin):
    pass\n\n\n"""
# registration_template = """admin.site.register({ModelName}, {ModelName}Admin)\n"""

for arg in sys.argv[1:]:
    if arg[0] == '*':
        t = 'from {} import *'.format(arg[1:])
    else:
        t = 'import {}'.format(arg)
    res += t + '\n'
    exec(t)

res += '\n'

av = {**locals()}
models = []
for local in av:
    if isinstance(av[local], django.db.models.base.ModelBase):
        models.append((local, av[local]))

for model_data in models:
    res += model_admin_template_with_fields.format(
        ModelName=model_data[0],
        fields=', '.join(
            '"{}"'.format(field if isinstance(field, str) else field.name)
            for field in (model_data[1].get_list_display(
            ) if hasattr(model_data[1], 'get_list_display') else model_data[1].
                          _meta.fields[1:])) + ', ')

# for model_data in models:
#     res += registration_template.format(ModelName=model_data[0])

print(res)
