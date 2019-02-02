"""
This is the main runner file of TelegramProblemGenerator.
Just call run function and it will continuously update all bots from Bot table.
The bot's updates won't be accepted if last update was more than 24 hours ago and will ask you for further actions.
All logs are collected in the logs.txt.
"""

import sys
import os
import logging
import time
from datetime import datetime
from threading import Thread
import django

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'TelegramProblemGenerator.settings')

django.setup()
from django.utils import timezone
from main.worker import *

bots = Bot.objects.all()
running = True


def run():
    """ Will run main cycle and continuously load updates of bots """
    print("Ready.")
    for bot in bots:
        for binding in bot.botbinding_set.all():
            if binding.participant_group.activeProblem:
                print('{} - {} - {} -> {} right answers'.format(
                    bot.name, bot.last_updated, binding.participant_group,
                    len(
                        Answer.objects.filter(
                            problem=binding.participant_group.activeProblem,
                            group_specific_participant_data__participant_group=
                            binding.participant_group,
                            right=True,
                            processed=False))))
        td = datetime.now(timezone.utc) - bot.last_updated
        print("[{}] {} since last update.".format(bot.name, td))
        if (td.days):
            logging.info("***** UPDATE DATA FOR BOT {} *****".format(bot.name))
            logging.info(
                get_response(
                    bot.base_url + "getUpdates",
                    payload={
                        'offset': bot.offset or "",
                        'timeout': 0
                    }))
            if input(
                    "WARNING: The data can be not up-to-date, so you'll get all the updates in the logs, do you want to continue? y/N: "
            ) != 'y':
                return

    def update(bot):
        while running:
            try:
                update_bot(bot)
            except Exception as e:
                logging.warning("ERROR: {}".format(e))
                time.sleep(1)

    ts = []
    for bot in bots:
        t = Thread(target=update, args=(bot,))
        t.daemon = True
        t.start()
        ts.append(t)
    for t in ts:
        t.join()


if __name__ == '__main__':
    run()
