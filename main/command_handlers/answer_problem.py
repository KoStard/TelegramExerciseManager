import logging
from main.models import Problem, MessageInstance, ActionType
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator
from datetime import datetime
from django.utils import timezone


def answer_problem(worker):
    """ Will send the answer of the problem -> automatically is answering to the active problem """
    if not worker.source.participant_group.activeProblem and len(
            worker.source.raw_text.split()) <= 1:
        worker.source.bot.send_message(
            worker.source.participant_group,
            "There is no active problem for this participant_group.",
            reply_to_message_id=worker.source.message["message_id"],
        )
        return

    # Registering message instance
    if worker.source.command == 'answer':
        MessageInstance.objects.create(
            action_type=ActionType.objects.get(value='problem_command'),
            date=datetime.fromtimestamp(
                worker['message']["date"], tz=timezone.get_current_timezone()),
            message_id=worker.source.message['message_id'],
            participant=worker.participant,
            participant_group=worker.participant_group,
            text=worker.source.raw_text,
            current_problem=worker.participant_group.activeProblem)
    problem = worker.source.participant_group.activeProblem
    if len(worker.source.raw_text.split()) > 1:
        index = int(worker.source.raw_text.split()[1])
        if problem and index > problem.index:
            worker.source.bot.send_message(
                worker.source.participant_group,
                "You can't send new problem's answer without opening it.",
                reply_to_message_id=worker.source.message["message_id"],
            )
            return
        elif not problem or index < problem.index:
            try:
                problem = worker.source.participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                    index=index)
            except Problem.DoesNotExist:
                worker.source.bot.send_message(worker.source.participant_group,
                                               "Invalid problem number {}.")
            else:
                resps = worker.source.bot.send_message(
                    worker.source.participant_group, problem.get_answer())
                for resp in resps:
                    MessageInstance.objects.create(
                        action_type=ActionType.objects.get(
                            value='problem_associated'),
                        date=datetime.fromtimestamp(
                            resp["date"], tz=timezone.get_current_timezone()),
                        message_id=resp['message_id'],
                        participant=None,
                        participant_group=worker.participant_group,
                        text=None,
                        current_problem=problem)
                for problemimage in sorted(
                        problem.problemimage_set.filter(for_answer=True),
                        key=lambda img: img.id):
                    image = problemimage.image
                    try:
                        resp = worker.source.bot.send_image(
                            worker.source.participant_group,
                            open(image.path, "rb"),
                            caption="Image of problem N{}'s answer.".format(
                                problem.index),
                        )
                        worker.unilog(
                            "Sending image for problem {}'s answer".format(
                                problem.index))
                    except Exception as e:
                        worker.unilog(
                            "Can't send image {} for problem N{}'s answer.".
                            format(image, problem.index))
                        print(e)
                        logging.info(e)
                    else:
                        MessageInstance.objects.create(
                            action_type=ActionType.objects.get(
                                value='problem_associated'),
                            date=datetime.fromtimestamp(
                                resp["date"],
                                tz=timezone.get_current_timezone()),
                            message_id=resp['message_id'],
                            participant=None,
                            participant_group=worker.participant_group,
                            text=None,
                            current_problem=problem)
            return
    resps = worker.source.bot.send_message(worker.source.participant_group,
                                           problem.get_answer())
    for resp in resps:
        MessageInstance.objects.create(
            action_type=ActionType.objects.get(value='problem_associated'),
            date=datetime.fromtimestamp(
                resp["date"], tz=timezone.get_current_timezone()),
            message_id=resp['message_id'],
            participant=None,
            participant_group=worker.participant_group,
            text=None,
            current_problem=problem)

    for problemimage in sorted(
            problem.problemimage_set.filter(for_answer=True),
            key=lambda img: img.id):
        image = problemimage.image
        try:
            resp = worker.source.bot.send_image(
                worker.source.participant_group,
                open(image.path, "rb"),
                caption="Image of problem N{}'s answer.".format(problem.index),
            )
            worker.unilog("Sending image for problem {}'s answer".format(
                problem.index))
        except Exception as e:
            worker.unilog(
                "Can't send image {} for problem N{}'s answer.".format(
                    image, problem.index))
            print(e)
            logging.info(e)
        else:
            MessageInstance.objects.create(
                action_type=ActionType.objects.get(value='problem_associated'),
                date=datetime.fromtimestamp(
                    resp["date"], tz=timezone.get_current_timezone()),
                message_id=resp['message_id'],
                participant=None,
                participant_group=worker.participant_group,
                text=None,
                current_problem=problem)
    old_positions = worker.participant_group.get_participants_positions()
    resps = worker.source.bot.send_message(
        worker.source.participant_group,
        problem.close(worker.source.participant_group))
    for resp in resps:
        MessageInstance.objects.create(
            action_type=ActionType.objects.get(value='problem_associated'),
            date=datetime.fromtimestamp(
                resp["date"], tz=timezone.get_current_timezone()),
            message_id=resp['message_id'],
            participant=None,
            participant_group=worker.participant_group,
            text=None,
            current_problem=problem)

    new_positions = worker.participant_group.get_participants_positions()
    worker.source.position_change = {
        key: old_positions[key] - new_positions[key]
        for key in new_positions
    }
    t_pages = worker.source.participant_group.telegraphpage_set.all()
    if t_pages:  # Create the page manually with DynamicTelegraphPageCreator
        t_page = t_pages[
            len(t_pages) -
            1]  # Using last added page -> negative indexing is not supported
        t_account = t_page.account
        page_controller = DynamicTelegraphPageCreator(t_account.access_token)
        page_controller.load_and_set_page(t_page.path, return_content=False)
        page_controller.update_page(
            content=worker.createGroupLeaderBoardForTelegraph())
    worker.source.participant_group.activeProblem = None
    worker.source.participant_group.save()
