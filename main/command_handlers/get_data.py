from django.core.management import call_command
import os
from main import program_settings
from datetime import datetime
from io import StringIO


def get_data(worker):
    """
    Will generate and send DB data as json file
    """
    buffer = StringIO()
    call_command('dumpdata', 'main', stdout=buffer)
    buffer.seek(0)
    worker.bot.send_document(worker.administrator_page, buffer, caption='Data of {}'.format(datetime.now().isoformat()),
                             reply_to_message_id=worker.message['message_id'])
