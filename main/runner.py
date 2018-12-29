import sys
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TelegramProblemGenerator.settings')
import django

django.setup()

from main.worker import *

group = Group.objects.get(id=1)
bot = Bot.objects.all()[0]
problem = Problem.objects.get(index=180)


bots = Bot.objects.all()
running = True


def run():
    print("Ready.")
    while running:
        for bot in bots:
            try:
                update_bot(bot)
            except Exception as e:
                print("ERROR: {}".format(e))
        if not running:
            break
        sleep(1)

run()
