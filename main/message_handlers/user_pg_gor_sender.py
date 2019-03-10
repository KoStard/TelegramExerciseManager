"""
Get Or Register user participant in participant groups
"""

from main.universals import get_from_Model, safe_getter
from main.models import Participant, GroupSpecificParticipantData
from main.data_managers import user_registry


def get_or_register_message_sender_participant(worker) -> Participant:
    """
    Will get if registered or register message sender as a participant
    """
    if worker.source.get('message'):
        participant = get_from_Model(
            Participant, id=worker['message']['from']['id'])
        if not participant:
            participant = user_registry.register_participant(worker['message']['from'])
        worker.source.participant = participant
        worker.source.is_from_superadmin = not not safe_getter(worker.participant, 'superadmin')
        return participant
    else:
        worker.source.participant = None
        worker.source.is_from_superadmin = False
        raise ValueError("INVALID MESSAGE DATA")


def get_or_register_groupspecificparticipantdata_of_active_participant(
        worker) -> GroupSpecificParticipantData:
    """
    Will get if registered or register participant in active participant_group
    """
    if worker['participant_group'] and worker['participant']:
        gspd = get_from_Model(
            worker['participant'].groupspecificparticipantdata_set,
            participant_group=worker['participant_group'], _mode='direct')
        if not gspd:
            gspd = user_registry.register_groupspecificparticipantdata(
                participant=worker['participant'],
                participant_group=worker['participant_group'])
        worker.source.groupspecificparticipantdata = gspd
        return gspd
    else:
        worker.source.groupspecificparticipantdata = None
        raise ValueError(
            "INVALID DATA IN get_or_register_groupspecificparticipantdata_of_active_participant"
        )
