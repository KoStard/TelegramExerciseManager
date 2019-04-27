import re
from main.universals import get_from_Model
from main.models import ViolationType


def check_message_validity(worker):
    """
    Will check message validity with multiple criteria.
    """
    criteria = (check_message_language, check_message_length)
    for criterion in criteria:
        if not criterion(worker):
            return False
    return True


def check_message_language(worker):
    """
    Checking message language
    Default - only English
    """
    current_language = 'English'
    current_language_regex = re.compile('^[a-zA-Z0-9?<>&#^_\'",.;:| +`/\\\s{}\[\]=~!@#$%^&*()£€•₽-]+$')
    if worker.source.raw_text and not current_language_regex.match(
            worker.source.raw_text) and not worker.is_from_superadmin:
        worker.answer_to_the_message(
            "Your message will be removed, because only {} characters are allowed.".format(current_language))
        worker.bot.delete_message(worker.source.participant_group, worker.source.message['message_id'])
        worker.source.groupspecificparticipantdata.create_violation(
            get_from_Model(ViolationType, value='language_restriction'), worker=worker)
        return False
    return True


TEXT_MAX_LENGTH = 400


def check_message_length(worker):
    """
    Will check message length
    """
    if len(worker.source.raw_text) > TEXT_MAX_LENGTH and \
            worker.source.groupspecificparticipantdata.highest_role.priority_level <= 0 and \
            not worker.source.is_from_superadmin:  # Recruit
        worker.answer_to_the_message(
            f"Your message will be removed, because you don't have "
            f"permissions to send messages with length more than {TEXT_MAX_LENGTH}.")
        worker.bot.delete_message(worker.source.participant_group, worker.source.message['message_id'])
        worker.source.groupspecificparticipantdata.create_violation(
            get_from_Model(ViolationType, value='long_message_restriction'), worker=worker)
        return False
    return True
