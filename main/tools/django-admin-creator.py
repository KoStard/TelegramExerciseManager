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
    list_display=({fields}
    )\n
{getters}\n\n"""
model_admin_template_without_fields = """\
@admin.register({ModelName})
class {ModelName}Admin(admin.ModelAdmin):
    pass\n\n"""
getter_template = """\
    def {GetterName}(current, self):
        return {Getter}\n\n"""
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
    fields = ''
    getters = ''
    for field in (model_data[1].get_list_display() if hasattr(
            model_data[1], 'get_list_display') else
                  model_data[1]._meta.fields[1:]):
        if isinstance(field, django.db.models.Field):
            field = field.name
        elif not isinstance(field, str):
            getters += getter_template.format(
                GetterName=field[0], Getter=field[1])
            field = field[0]
        fields += '\n        "{}", '.format(field)

    res += model_admin_template_with_fields.format(
        ModelName=model_data[0], fields=fields, getters=getters)

# for model_data in models:
#     res += registration_template.format(ModelName=model_data[0])

print(res)
