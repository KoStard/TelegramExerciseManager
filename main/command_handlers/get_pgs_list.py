from main.models import ParticipantGroup


def get_pgs_list(worker):
    """
    Will send participant groups list to the coming administrator page
    """
    worker.source.bot.send_message(
        worker.source.message['chat']['id'],
        '\n'.join(f'{index + 1} - {pg_name}' for index, pg_name in enumerate(
            ('*' if pg.get_administrator_page() else '') + pg.title for pg in ParticipantGroup.objects.all()))
    )
