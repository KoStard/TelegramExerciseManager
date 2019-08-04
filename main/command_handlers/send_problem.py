import logging
from main.models import Problem, MessageInstance, ActionType
from main.data_managers.user_registry import register_current_participant_group_members_count
from os import path
from datetime import datetime
from django.utils import timezone


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
        if not worker.source.participant_group.activeSubjectGroupBinding.last_problem:
            worker.answer_to_the_message(
                "There was no active problem in this group, so use the command like this - /send 1")
            return
        problem: Problem = worker.source.participant_group.activeSubjectGroupBinding.last_problem.next
        if not problem:
            worker.source.bot.send_message(
                worker.source.participant_group,
                'The subject is finished, no problem to send.',
                reply_to_message_id=worker.source.message["message_id"],
            )
            return

    # Registering message instance with updated active problem
    if worker.source.command == 'send':
        MessageInstance.objects.create(
            action_type=ActionType.objects.get(value='problem_command'),
            date=datetime.fromtimestamp(
                worker['message']["date"],
                tz=timezone.get_current_timezone()),
            message_id=worker.source.message['message_id'],
            participant=worker.participant,
            participant_group=worker.participant_group,
            text=worker.source.raw_text,
            current_problem=problem
        )
    
    form_resp = worker.source.bot.send_message(worker.source.participant_group, str(problem))

    for resp in form_resp:
        MessageInstance.objects.create(
            action_type=ActionType.objects.get(value='problem_associated'),
            date=datetime.fromtimestamp(
                resp["date"],
                tz=timezone.get_current_timezone()),
            message_id=resp['message_id'],
            participant=None,
            participant_group=worker.participant_group,
            text=None,
            current_problem=problem
        )

    logging.debug("Sending problem {}".format(problem.index))
    logging.debug(form_resp)
    for problemimage in sorted(problem.problemimage_set.filter(for_answer=False), key=lambda img: img.id):
        image = problemimage.image
        try:
            resps = worker.source.bot.send_image(
                worker.source.participant_group,
                open(image.path, "rb"),
                reply_to_message_id=form_resp[0].get(
                    "message_id"),  # Temporarily disabling
                caption="Image of problem N{}.".format(problem.index),
            )
            for resp in resps:
                MessageInstance.objects.create(
                    action_type=ActionType.objects.get(value='problem_associated'),
                    date=datetime.fromtimestamp(
                        resp["date"],
                        tz=timezone.get_current_timezone()),
                    message_id=resp['message_id'],
                    participant=None,
                    participant_group=worker.participant_group,
                    text=None,
                    current_problem=problem
                )
            logging.debug("Sending image for problem {}".format(problem.index))
            worker.adm_log("Sent image {} for problem N{}".format(
                path.basename(image.name), problem.index))
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
    register_current_participant_group_members_count(worker)  # Registering participants count with send command
