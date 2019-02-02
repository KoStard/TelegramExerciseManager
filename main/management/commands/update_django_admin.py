from django.core.management.base import BaseCommand, CommandError
from main.tools.django_admin_creator import create


class Command(BaseCommand):
    help = 'Update Django Admin'

    def handle(self, *args, **options):
        open('main/admin.py', 'w').write(create(['*main.models']))
        print("Done")