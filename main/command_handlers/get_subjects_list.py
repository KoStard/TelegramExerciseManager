def get_subjects_list(worker):
    """ Will send subjects list for current group """
    worker.source.bot.send_message(
        worker.source.participant_group,
        """This is the subjects list for current group:\n{}""".format('\n'.join(
            ' - '.join(str(e) for e in el)
            for el in enumerate((binding.subject.name
                                 for binding in worker.source.participant_group.
                                subjectgroupbinding_set.all()), 1))),
        reply_to_message_id=worker.source.message['message_id'])
