import subprocess
from io import StringIO


def git_pull(worker):
    worker.answer_to_the_message(
        "Finished, here is the output:\n{}".format(subprocess.check_output(['git', 'pull']).decode('utf-8')))
