#!/usr/bin/env python

"""
This is the main runner file of TelegramProblemGenerator.
Just call run function and it will continuously update all bots from Bot table.
The bot's updates won't be accepted if last update was more than 24 hours ago and will ask you for further actions.
All logs are collected in the logs.txt.
"""

import sys
import os
import platform
import logging
import time
from datetime import datetime
from threading import Thread
import django

from os.path import getmtime


def get_listening_files(base=None):
    res = []
    if not base:
        base = os.path.abspath(os.getcwd()+ '/../..')
    for fl in os.listdir(base):
        current = os.path.join(base, fl)
        if os.path.isfile(current):
            if current.split('.')[-1] == 'py':
                res.append(current)
        else:
            res += get_listening_files(current)
    return res

WATCHED_FILES = get_listening_files()
WATCHED_FILES_MTIMES = [(f, getmtime(f)) for f in WATCHED_FILES]


BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'TelegramProblemGenerator.settings')

django.setup()
from django.utils import timezone
from main.worker import *
from django.core.management import call_command

running = True
file_checks = 0

autorestart = True
def run(bots, *, testing=False):
    """ Will run main cycle and continuously load updates of bots """
    global autorestart
    for bot in bots:
        for binding in bot.botbinding_set.all():
            adm_p = binding.participant_group.get_administrator_page()
            if adm_p:
                bot.send_message(adm_p, "Started...")
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
        global running, file_checks, autorestart
        while running:
            if file_checks % 20 < 2:
                if get_listening_files() != WATCHED_FILES and autorestart and platform.system() != 'Windows':
                    running = False
                    return

            file_checks += 1
            for f, mtime in WATCHED_FILES_MTIMES:
                if getmtime(f) != mtime and autorestart and platform.system() != 'Windows':
                    running = False
                    print("Found changed file!")
                    return
            # try:
            if running:
                update_bot(bot)
            # except Exception as e:
            #     logging.warning("ERROR: {}".format(e))
            #     time.sleep(1)

    ts = []
    for bot in bots:
        t = Thread(target=update, args=(bot,))
        t.daemon = True
        t.start()
        ts.append(t)
    for t in ts:
        t.join()

    if autorestart and platform.system() != 'Windows' and not running:
        call_command('migrate') # Test
        # Restarting the script if on macOS or Linux -> has to be executable -> chmod a+x runner.py
        # Won't match new python files
        print("Migrating...")
        os.execv(sys.executable,['python3.7']+ sys.argv)


if __name__ == '__main__':
    testing = False
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("*****************--IN THE TESTING MODE--*****************")
        bots = Bot.objects.filter(for_testing=True)
        testing = True
    else:
        print("*****************--IN THE STANDARD MODE--*****************")
        bots = Bot.objects.all()
    run(bots, testing=testing)
