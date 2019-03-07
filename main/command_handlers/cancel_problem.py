from main.models import Answer


def cancel_problem(worker):
    """ Will cancel the problem and remove all answers from the DB.  """
    if worker.source.participant_group.activeProblem:
        answers = [answer for answer in Answer.objects.filter(
            group_specific_participant_data__participant_group=worker.source.participant_group,
            problem=worker.source.participant_group.activeProblem)]
        for answer in answers:
            answer.delete()
        worker.source.participant_group.activeSubjectGroupBinding.last_problem = worker.source.participant_group.activeProblem.previous
        worker.source.participant_group.activeSubjectGroupBinding.save()
        temp_problem = worker.source.participant_group.activeProblem
        worker.source.participant_group.activeProblem = None
        worker.source.participant_group.save()
        worker.source.bot.send_message(
            worker.source.participant_group,
            "The problem {} is cancelled.".format(temp_problem.index),
            reply_to_message_id=worker.source.message['message_id'])
    else:
        worker.source.bot.send_message(
            worker.source.participant_group,
            "There is not active problem to cancel.",
            reply_to_message_id=worker.source.message['message_id'])
