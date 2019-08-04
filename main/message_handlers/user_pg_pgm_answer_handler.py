"""
Will handle answer of participant group member in participant group
"""

from main.universals import get_from_Model
from main.models import Answer, MessageInstance, ActionType
from datetime import datetime
from django.utils import timezone


def handle_answer(worker):
    """
    Will handle participant answers
    """
    if not worker['participant_group'].activeProblem:
        print(f"There is no active problem in {worker['participant_group']}")
        return False
    old_answer = get_from_Model(
        worker['participant_group'].activeProblem.answer_set,
        group_specific_participant_data=worker[
            'groupspecificparticipantdata'],
        processed=False,
        _mode='direct')
    worker.source.old_answer = old_answer
    if old_answer:
        handle_answer_change(worker)
    elif worker['bot'].for_testing:
        handle_answers_from_testing_bots(worker)
    else:
        accept_answer(worker)


def handle_answer_change(worker):
    """
    Catching when participant is trying to change the answer
    """
    if not worker.get('bot') or not worker.get('message'):
        return
    if worker['old_answer'].answer.upper() == worker['variant'].upper():
        # Sending same answer again
        worker.unilog("{} is trying to answer {} again".format(
            worker['participant'], worker['variant']))
        worker['bot'].delete_message(worker['participant_group'],
                                     worker['message']['message_id'])
    else:
        worker.unilog("{} is trying to change answer {} to {}".format(
            worker['participant'], worker['old_answer'].answer,
            worker['variant']))
        worker['bot'].send_message(
            worker['participant_group'],
            'Dear {}, you can\'t change your answer (your accepted answer is {}).'.format(
                worker['participant'].name, worker['old_answer'].answer),
            reply_to_message_id=worker['message']['message_id'])


def handle_answers_from_testing_bots(worker):
    """
    Will handle answers from testing bots
    """
    worker.unilog("Answer from testing bot's controlling groups")

    # Registering message instance
    MessageInstance.objects.create(
        action_type=ActionType.objects.get(value='participant_answer'),
        date=datetime.fromtimestamp(
            worker['message']["date"],
            tz=timezone.get_current_timezone()),
        message_id=worker.source.message['message_id'],
        participant=worker.participant,
        participant_group=worker.participant_group,
        text=worker.source.raw_text,
        current_problem=worker.participant_group.activeProblem
    )


def accept_answer(worker) -> Answer:
    """
    Accepting answer - right or wrong
    """
    if worker['variant'] == worker['participant_group'].activeProblem.right_variant.upper():
        print("Right answer from {} N{}".format(
            worker['participant'],
            len(
                worker['participant_group'].activeProblem.answer_set.filter(
                    right=True,
                    processed=False,
                    group_specific_participant_data__participant_group=
                    worker['participant_group'])) + 1))
    else:
        print("Wrong answer from {} - Right answers {}".format(
            worker['participant'],
            len(
                worker['participant_group'].activeProblem.answer_set.filter(
                    right=True,
                    processed=False,
                    group_specific_participant_data__participant_group=worker[
                        'participant_group']))))

    # Registering message instance
    MessageInstance.objects.create(
        action_type=ActionType.objects.get(value='participant_answer'),
        date=datetime.fromtimestamp(
            worker['message']["date"],
            tz=timezone.get_current_timezone()),
        message_id=worker.source.message['message_id'],
        participant=worker.participant,
        participant_group=worker.participant_group,
        text=worker.source.raw_text,
        current_problem=worker.participant_group.activeProblem
    )
    
    answer = Answer(
        problem=worker['participant_group'].activeProblem,
        answer=worker['variant'],
        right=worker['variant'] == worker['participant_group'].activeProblem.right_variant.upper(),
        processed=False,
        group_specific_participant_data=worker['groupspecificparticipantdata'],
        date=datetime.fromtimestamp(
                worker['message']["date"],
                tz=timezone.get_current_timezone()),
    )
    answer.save()
    return answer
