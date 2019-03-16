from main.models import Subject, SubjectGroupBinding


def unbind_subject(worker):
    """
    Will unbind subject from group from administrator_page -> for superadmins
    Get index with /subjects_list
    """
    if not worker.source.command_argv or not worker.source.command_argv[0].isdecimal():
        worker.bot.send_message(
            worker.administrator_page,
            "You have to give subject's index with the command - get index with /subjects_list command.",
            reply_to_message_id=worker.source.message['message_id']
        )
        return False
    if not worker.source.administrator_page.participant_group:
        worker.answer_to_the_message(
            ("This administrator page is not bound with any participant group, "
             "you can bind it with /pgs_list and /start_admin [index]"),
        )
        return False
    index = int(worker.source.command_argv[0]) - 1
    subject_bindings = worker.source.administrator_page.participant_group.subjectgroupbinding_set.all()
    if 0 <= index < len(subject_bindings):
        subject_binding = subject_bindings[index]
    else:
        worker.answer_to_the_message("You have to give valid index - get index with /subjects_list command.")
        return False
    subject_binding = subject_bindings[index]
    subject_binding.delete()
    worker.answer_to_the_message(
        (f"Congratulations, now subject {subject_binding.subject.name} is "
         f"unbound from {worker.administrator_page.participant_group.title}."))
