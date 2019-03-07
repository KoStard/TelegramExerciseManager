def select_subject(worker):
    """ Will select subject in the group
            Give with message
             - index
            """
    if not ' ' in worker.source.raw_text or not worker.source.raw_text.split(' ')[1].isnumeric():
        worker.source.bot.send_message(
            worker.source.participant_group,
            """You have to give the index of subject to select.\nYou can get indexes with /subjects_list command.""",
            reply_to_message_id=worker.source.message['message_id'])
        return
    index = int(worker.source.raw_text.split(' ')[1])
    subject_group_bindings = worker.source.participant_group.subjectgroupbinding_set.all()
    if index not in range(1, len(subject_group_bindings) + 1):
        worker.source.bot.send_message(
            worker.source.participant_group,
            """You have to give valid subject index.\nYou can get indexes with /subjects_list command.""",
            reply_to_message_id=worker.source.message['message_id'])
        return
    worker.source.participant_group.activeSubjectGroupBinding = subject_group_bindings[index
                                                                                       - 1]
    worker.source.participant_group.activeProblem = None
    worker.source.participant_group.save()
    worker.source.bot.send_message(
        worker.source.participant_group,
        """Subject "{}" is now selected.""".format(
            subject_group_bindings[index - 1].subject.name),
        reply_to_message_id=worker.source.message['message_id'])
