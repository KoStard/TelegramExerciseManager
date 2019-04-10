from django.core.management import call_command
import os
from io import StringIO
from pathlib import Path


def load_data(worker):
    """
    Will load data from given JSON file
    """
    if 'document' not in worker.message:
        worker.answer_to_the_message("You have to send file with the command.")
        return
    file_id = worker.message['document']['file_id']
    file_name = worker.message['document'].get('file_name')
    if not file_name.endswith('.json'):
        file_name += '.json'
    f = worker.bot.get_file_info(file_id)
    file_path = f.get('file_path')
    base_path = Path(__file__)
    if file_path:
        with open(file_name, 'wb') as f:
            f.write(worker.bot.get_file(file_path))
        output = StringIO()
        call_command('loaddata', str(base_path.parent.parent / file_name), stdout=output)
    os.remove(file_name)
    output.seek(0)
    worker.answer_to_the_message("Done!, Here is the output:\n{}".format(output.read(1000)))
