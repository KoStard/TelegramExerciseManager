# Generated by Django 2.2.4 on 2019-08-04 10:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0052_messageinstance_active_problem'),
    ]

    operations = [
        migrations.RenameField(
            model_name='messageinstance',
            old_name='active_problem',
            new_name='current_problem',
        ),
    ]
