from django.core.management import call_command
from datetime import datetime
from io import StringIO


def dump_data(worker):
    """
    Will generate and send DB data as json file
    """
    buffer = StringIO()
    models = ' '.join(worker.source.command_argv)
    if not models:
        worker.answer_to_the_message("You have to give model names to export - like main.TelegramCommand")
        return
    call_command('dumpdata', models, stdout=buffer)
    buffer.seek(0)
    worker.bot.send_document(worker.administrator_page, buffer, caption='Data of {}'.format(datetime.now().isoformat()),
                             reply_to_message_id=worker.message['message_id'])
