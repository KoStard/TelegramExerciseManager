from django.core.management import call_command


def migrate(worker):
    """
    Will run all migrations
    """
    call_command('migrate')
    worker.answer_to_the_message("Done!")
