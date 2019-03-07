def send(source: dict) -> None:
    """ Will send problem -> default will be the next problem if available"""
    if participant_group.activeProblem:
        bot.send_message(
            participant_group,
            "You have to close active problem before sending another one.",
            reply_to_message_id=message['message_id'])
        return
    if len(text.split()) > 1:
        index = int(text.split()[1])
        try:
            problem: Problem = participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                index=index)
        except Problem.DoesNotExist:
            bot.send_message(
                participant_group,
                'Invalid problem number "{}".'.format(index),
                reply_to_message_id=message["message_id"],
            )
            return
        except AttributeError:  # If there is no activeSubjectGroupBinding
            bot.send_message(
                participant_group,
                'There is no active subject for this group.',
                reply_to_message_id=message["message_id"],
            )
            return
    else:
        problem: Problem = participant_group.activeSubjectGroupBinding.last_problem.next
        if not problem:
            bot.send_message(
                participant_group,
                'The subject is finished, no problem to send.',
                reply_to_message_id=message["message_id"],
            )
            return
    form_resp = bot.send_message(participant_group, str(problem))
    logging.debug("Sending problem {}".format(problem.index))
    logging.debug(form_resp)
    for problemimage in problem.problemimage_set.filter(for_answer=False):
        image = problemimage.image
        try:
            bot.send_image(
                participant_group,
                open(image.path, "rb"),
                reply_to_message_id=form_resp[0].get(
                    "message_id"),  # Temporarily disabling
                caption="Image of problem N{}.".format(problem.index),
            )
            logging.debug("Sending image for problem {}".format(problem.index))
            adm_log(
                bot, participant_group, "Sent image {} for problem N{}".format(
                    image, problem.index))
        except Exception as e:
            print("Can't send image {}".format(image))
            print(e)
            logging.info(e)
            adm_log(
                bot, participant_group,
                "Can't send image {} for problem N{}".format(
                    image, problem.index))
    participant_group.activeProblem = problem
    participant_group.save()
    participant_group.activeSubjectGroupBinding.last_problem = problem
    participant_group.activeSubjectGroupBinding.save()
