def status_in_administrator_page(worker):
    """ Will log the status to the administrator page """
    try:
        answers = worker.source.administrator_page.participant_group.activeProblem.answer_set.filter(
            processed=False,
            group_specific_participant_data__participant_group=
            worker.source.administrator_page.participant_group)
    except AttributeError:  # If there is no active problem
        worker.source.bot.send_message(
            worker.source.administrator_page,
            """There is no active problem.""",
            reply_to_message_id=worker.source.message['message_id'])
        return
    answers_count = [el for el in ((
        variant,
        len([answer for answer in answers
             if answer.answer.upper() == variant]))
        for variant in 'ABCDE') if el[1]]
    worker.source.bot.send_message(
        worker.source.administrator_page,
        """Current status for problem {} is{}\nFor more contact with @KoStard""".format(
            worker.source.administrator_page.participant_group.activeProblem.index,
            ''.join('\n{} - {}'.format(*el) for el in answers_count)
            if answers_count else ' - No one answered.'),
        reply_to_message_id=worker.source.message['message_id'])
