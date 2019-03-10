"""
Will handle message bindings from user in participant groups
"""

import logging
from main.universals import get_from_Model
from main.models import ViolationType

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
                "Dear {}, your message will be removed, because {}.\nYou have [{}] roles.\
                \nFor more information contact with @KoStard".format(
                    worker['participant'].name,
                    ', '.join(message_bindings_check_response["cause"]),
                    ", ".join("{} - {}".format(
                        participantgroupbinding.role.name,
                        participantgroupbinding.role.priority_level,
                    ) for participantgroupbinding in
                              worker['groupspecificparticipantdata'].
                              participantgroupbinding_set.all()),
                ),
                reply_to_message_id=worker['message']["message_id"],
            )
            worker['bot'].delete_message(worker['participant_group'],
                                         worker['message']["message_id"])
            worker['groupspecificparticipantdata'].create_violation(
                get_from_Model(
                    ViolationType,
                    value='message_binding_low_permissions'))
            return False
    return True
