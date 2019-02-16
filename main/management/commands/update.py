from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Update = makemigrations + migrate + update_django_admin'

    def handle(self, *args, **options):
        call_command('makemigrations')
        call_command('migrate')
        call_command('update_django_admin')