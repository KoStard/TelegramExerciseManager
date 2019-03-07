def get_active_subject(worker):
    """ Will send active subject to the group if available """
    if worker.source.participant_group.activeSubjectGroupBinding:
        worker.source.bot.send_message(
            worker.source.participant_group,
            """Subject "{}" is active.""".format(
                worker.source.participant_group.activeSubjectGroupBinding.subject.name),
            reply_to_message_id=worker.source.message['message_id'])
    else:
        worker.source.bot.send_message(
            worker.source.participant_group,
            """There is no active subject in this group.""",
            reply_to_message_id=worker.source.message['message_id'])
