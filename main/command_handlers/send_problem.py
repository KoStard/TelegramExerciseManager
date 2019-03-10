import logging
from main.models import Problem


def send_problem(worker) -> None:
    """ Will send problem -> default will be the next problem if available"""
    if worker.source.participant_group.activeProblem:
        worker.source.bot.send_message(
            worker.source.participant_group,
            "You have to close active problem before sending another one.",
            reply_to_message_id=worker.source.message['message_id'])
        return
    if len(worker.source.raw_text.split()) > 1:
        index = int(worker.source.raw_text.split()[1])
        try:
            problem: Problem = worker.source.participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                index=index)
        except Problem.DoesNotExist:
            worker.source.bot.send_message(
                worker.source.participant_group,
                'Invalid problem number "{}".'.format(index),
                reply_to_message_id=worker.source.message["message_id"],
            )
            return
        except AttributeError:  # If there is no activeSubjectGroupBinding
            worker.source.bot.send_message(
                worker.source.participant_group,
                'There is no active subject for this group.',
                reply_to_message_id=worker.source.message["message_id"],
            )
            return
    else:
        problem: Problem = worker.source.participant_group.activeSubjectGroupBinding.last_problem.next
        if not problem:
            worker.source.bot.send_message(
                worker.source.participant_group,
                'The subject is finished, no problem to send.',
                reply_to_message_id=worker.source.message["message_id"],
            )
            return
    form_resp = worker.source.bot.send_message(worker.source.participant_group, str(problem))
    logging.debug("Sending problem {}".format(problem.index))
    logging.debug(form_resp)
    for problemimage in sorted(problem.problemimage_set.filter(for_answer=False), key=lambda img: img.id):
        image = problemimage.image
        try:
            worker.source.bot.send_image(
                worker.source.participant_group,
                open(image.path, "rb"),
                reply_to_message_id=form_resp[0].get(
                    "message_id"),  # Temporarily disabling
                caption="Image of problem N{}.".format(problem.index),
            )
            logging.debug("Sending image for problem {}".format(problem.index))
            worker.adm_log("Sent image {} for problem N{}".format(
                image, problem.index))
        except Exception as e:
            print("Can't send image {}".format(image))
            print(e)
            logging.info(e)
            worker.adm_log(
                "Can't send image {} for problem N{}".format(
                    image, problem.index))
    worker.source.participant_group.activeProblem = problem
    worker.source.participant_group.save()
    worker.source.participant_group.activeSubjectGroupBinding.last_problem = problem
    worker.source.participant_group.activeSubjectGroupBinding.save()
