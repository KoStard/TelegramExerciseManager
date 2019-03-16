from main.models import Subject, SubjectGroupBinding


def bind_subject(worker):
    """
    Will bind subject with the group from administrator_page -> for superadmins
    /bind_subject index
    index - from /all_subjects_list
    """
    if not worker.source.command_argv or not worker.source.command_argv[0].isdecimal():
        worker.bot.send_message(
            worker.administrator_page,
            "You have to give subject's index with the command - get index with /all_subjects_list command.",
            reply_to_message_id=worker.source.message['message_id']
        )
        return False
    index = int(worker.source.command_argv[0]) - 1
    subjects = Subject.objects.all()
    if 0 <= index < len(subjects):
        subject = subjects[index]
    else:
        worker.bot.send_message(
            worker.administrator_page,
            "You have to give valid index - get index with /all_subjects_list command.",
            reply_to_message_id=worker.source.message['message_id']
        )
        return False
    if not worker.source.administrator_page.participant_group:
        worker.bot.send_message(
            worker.administrator_page,
            ("This administrator page is not bound with any participant group, "
             "you can bind it with /pgs_list and /start_admin [index]"),
            reply_to_message_id=worker.source.message['message_id']
        )
        return False
    sgb = SubjectGroupBinding.objects.create(
        subject=subject,
        participant_group=worker.administrator_page.participant_group,
    )
    worker.answer_to_the_message(
        (f"Congratulations, now subject {subject.name} is "
         f"bound with {worker.administrator_page.participant_group.title}."))
