import re


def check_message_validity(worker):
    """
    Will check message validity with multiple criteria.
    """
    criteria = (check_message_language,)
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
    if not current_language_regex.match(worker.source.raw_text) and not worker.is_from_superadmin:
        worker.answer_to_the_message(
            "Your message will be removed, because only {} characters are allowed.".format(current_language))
        worker.bot.delete_message(worker.source.participant_group, worker.source.message['message_id'])
