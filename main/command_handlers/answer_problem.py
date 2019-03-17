import logging
from main.models import Problem
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator


def answer_problem(worker):
    """ Will send the answer of the problem -> automatically is answering to the active problem """
    if not worker.source.participant_group.activeProblem and len(worker.source.raw_text.split()) <= 1:
        worker.source.bot.send_message(
            worker.source.participant_group,
            "There is no active problem for this participant_group.",
            reply_to_message_id=worker.source.message["message_id"],
        )
        return
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
                worker.source.bot.send_message(worker.source.participant_group, problem.get_answer())
                for problemimage in sorted(problem.problemimage_set.filter(for_answer=True), key=lambda img: img.id):
                    image = problemimage.image
                    try:
                        worker.source.bot.send_image(
                            worker.source.participant_group,
                            open(image.path, "rb"),
                            caption="Image of problem N{}'s answer.".format(problem.index),
                        )
                        worker.unilog("Sending image for problem {}'s answer".format(problem.index))
                    except Exception as e:
                        worker.unilog("Can't send image {} for problem N{}'s answer.".format(
                            image, problem.index))
                        print(e)
                        logging.info(e)
            return
    worker.source.bot.send_message(worker.source.participant_group, problem.get_answer())
    for problemimage in sorted(problem.problemimage_set.filter(for_answer=True), key=lambda img: img.id):
        image = problemimage.image
        try:
            worker.source.bot.send_image(
                worker.source.participant_group,
                open(image.path, "rb"),
                caption="Image of problem N{}'s answer.".format(problem.index),
            )
            worker.unilog("Sending image for problem {}'s answer".format(problem.index))
        except Exception as e:
            worker.unilog("Can't send image {} for problem N{}'s answer.".format(
                image, problem.index))
            print(e)
            logging.info(e)
    worker.source.old_positions = worker.participant_group.get_participants_positions()
    worker.source.bot.send_message(worker.source.participant_group, problem.close(worker.source.participant_group))
    worker.source.new_positions = worker.participant_group.get_participants_positions()
    worker.source.position_change = {key: worker.source.new_positions[key] - worker.source.old_positions[key] for key in
                                     worker.source.new_positions}
    t_pages = worker.source.participant_group.telegraphpage_set.all()
    if t_pages:  # Create the page manually with DynamicTelegraphPageCreator
        t_page = t_pages[len(t_pages) -
            1]  # Using last added page -> negative indexing is not supported
        t_account = t_page.account
        page_controller = DynamicTelegraphPageCreator(t_account.access_token)
        page_controller.load_and_set_page(t_page.path, return_content=False)
        page_controller.update_page(
            content=worker.createGroupLeaderBoardForTelegraph())
    worker.source.participant_group.activeProblem = None
    worker.source.participant_group.save()
