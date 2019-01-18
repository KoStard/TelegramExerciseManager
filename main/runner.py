import django
import sys
import os
import logging
from datetime import datetime

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'TelegramProblemGenerator.settings')

django.setup()
from django.utils import timezone
from main.worker import *

group = Group.objects.get(id=1)
bot = Bot.objects.all()[0]
problem = Problem.objects.get(index=180)

bots = Bot.objects.all()
running = True


def run():
    print("Ready.")
    for bot in bots:
        for binding in bot.botbinding_set.all():
            if binding.group.activeProblem:
                print('{} - {} - {} -> {} right answers'.format(
                    bot.name, bot.last_updated, binding.group,
                    len(
                        Answer.objects.filter(
                            problem=binding.group.activeProblem,
                            group_specific_participant_data__group=binding.
                            group,
                            right=True,
                            processed=False))))
        td = datetime.now(timezone.utc) - bot.last_updated
        print("[{}] {} from last update.".format(bot.name, td))
        if (td.days):
            logging.info("***** UPDATE DATA FOR BOT {} *****".format(bot.name))
            logging.info(
                get_response(
                    bot.base_url + "getUpdates",
                    payload={
                        'offset': bot.offset or "",
                        'timeout': timeout
                    }))
            if input(
                    "WARNING: The data can be not up-to-date, so you'll get all the updates in the logs, do you want to continue? y/N: "
            ) != 'y':
                return
    while running:
        for bot in bots:
            try:
                update_bot(bot)
            except Exception as e:
                logging.warning("ERROR: {}".format(e))
        if not running:
            break
        sleep(1)


run()
