"""
Will handle message bindings from user in participant groups
"""

import logging
from main.universals import get_from_Model
from main.models import ViolationType
from main.templates import message_removal_message_with_highest_role_template

AVAILABLE_MESSAGE_BINDINGS = {
    "document": 0,
    "sticker": 0,
    "photo": 1,
    "audio": 2,
    "animation": 2,
    "voice": 2,
    "game": 3,
    "video": 3,
    "video_note": 3,
}


def check_message_bindings(worker):
    """ Will check message for bindings and check participant's permissions to use them """
    resp = {"status": True, "unknown": False}
    priority_level = worker[
        'groupspecificparticipantdata'].highest_role.priority_level
    for message_binding in AVAILABLE_MESSAGE_BINDINGS:
        if message_binding in worker['message'] and AVAILABLE_MESSAGE_BINDINGS[message_binding] > priority_level:
            if resp["status"]: resp["status"] = False
            if "cause" not in resp:
                resp["cause"] = []
            resp["cause"].append(
                "\"{}\" message binding is not allowed for users with priority level lower than {}"
                    .format(message_binding,
                            AVAILABLE_MESSAGE_BINDINGS[message_binding]))
    return resp


def handle_message_bindings(worker) -> bool:
    message_bindings_check_response = check_message_bindings(worker)
    if not message_bindings_check_response["status"]:
        logging.info(message_bindings_check_response["cause"])
        if not message_bindings_check_response["unknown"]:
            worker['bot'].send_message(
                worker['participant_group'],
                message_removal_message_with_highest_role_template.format(
                    name=worker['participant'].name,
                    cause=', '.join(message_bindings_check_response["cause"]),
                    highest_role=worker['groupspecificparticipantdata'].highest_role.name
                ),
                reply_to_message_id=worker['message']["message_id"],
            )
            worker['bot'].delete_message(worker['participant_group'],
                                         worker['message']["message_id"])
            worker['groupspecificparticipantdata'].create_violation(
                get_from_Model(
                    ViolationType,
                    value='message_binding_low_permissions'), worker=worker)
            return False
    return True


def has_message_bindings(worker) -> bool:
    return any(message_binding in worker.source.message for message_binding in AVAILABLE_MESSAGE_BINDINGS)
