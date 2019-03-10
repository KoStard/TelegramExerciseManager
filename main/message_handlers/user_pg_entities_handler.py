"""
Will handle entities from user in participant groups
"""

from main.universals import safe_getter, get_from_Model
from main.models import ViolationType
from datetime import datetime
from django.utils import timezone
import logging

AVAILABLE_ENTITIES = {
    "mention": -1,
    "hashtag": 1,
    "cashtag": 0,
    "bot_command": -1,
    "url": 2,
    "email": 1,
    "phone_number": 0,
    "bold": 0,
    "italic": 0,
    "code": 0,
    "pre": 0,
    "text_link": 3,
    "text_mention": -1,
}


def check_entities(worker):
    """ Will check message for entities and check participant's permissions to use them """
    resp = {"status": True, "unknown": False}
    priority_level = worker[
        'groupspecificparticipantdata'].highest_role.priority_level
    for entity in worker['entities']:
        entity = entity["type"]
        if entity not in AVAILABLE_ENTITIES:
            resp["status"] = False
            resp["cause"] = "Unknown entity {}".format(entity)
            resp["unknown"] = True
            break
        if AVAILABLE_ENTITIES[entity] > priority_level:
            resp["status"] = False
            resp[
                "cause"] = "{} entity is not allowed for users with priority level lower than {}".format(
                entity, AVAILABLE_ENTITIES[entity])
            break
    return resp


def handle_entities(worker) -> bool:
    """ Will handle entities from worker's message """
    entities = safe_getter(worker.source, 'message.entities', mode='dict', default=[])
    worker.entities = entities
    entities_check_response = check_entities(worker)
    worker.entities_check_response = entities_check_response
    logging.info("Found Entity: " + str(entities_check_response))
    if not entities_check_response["status"]:
        if not entities_check_response["unknown"]:
            # Sending answer message to the message with restricted entities
            worker['bot'].send_message(
                worker['participant_group'],
                "Dear {}, your message will be removed, because {}.\nYou have [{}] roles.\
                \nFor more information contact with @KoStard".format(
                    worker['participant'].name,
                    entities_check_response["cause"],
                    ", ".join("{} - {}".format(
                        participantgroupbinding.role.name,
                        participantgroupbinding.role.priority_level,
                    ) for participantgroupbinding in
                              worker['groupspecificparticipantdata'].
                              participantgroupbinding_set.all())
                    or '-',
                ),
                reply_to_message_id=worker['message']["message_id"],
            )
            # Removing message with restricted entities
            worker['bot'].delete_message(worker['participant_group'],
                                         worker['message']["message_id"])
            # Creating violation
            worker['groupspecificparticipantdata'].create_violation(
                get_from_Model(
                    ViolationType,
                    value='message_entity_low_permissions'),
                datetime.fromtimestamp(
                    worker['message']["date"],
                    tz=timezone.get_current_timezone()))
            return False
    return True
