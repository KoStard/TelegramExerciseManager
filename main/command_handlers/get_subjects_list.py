def get_subjects_list(worker):
    """ Will send subjects list for current group """
    worker.answer_to_the_message(
        """This is the subjects list for current group:\n{}""".format('\n'.join(
            ' - '.join(str(e) for e in el)
            for el in enumerate((binding.subject.name
                                 for binding in (
                                         worker.source.participant_group or
                                         worker.source.administrator_page.participant_group).
                                subjectgroupbinding_set.all()), 1)))
    )
