from main.models import Subject


def get_all_subjects_list(worker):
    """
    Will send all subjects list to the adm_page -> only for superadmins
    """
    worker.bot.send_message(
        worker.source.administrator_page,
        "All subjects list:\n" +
        '\n'.join(f'{index + 1} - {subject.name}' for index, subject in enumerate(Subject.objects.all())),
        reply_to_message_id=worker.source.message['message_id']
    )
