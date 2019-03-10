"""
Will register new members
"""

from main.universals import safe_getter, get_from_Model
from main.models import Participant
from main.data_managers import user_registry
from datetime import datetime
from django.utils import timezone


def register_participant_group_new_members(worker) -> list:
    """
    Will register all participant group new members
    """
    new_members = []
    for new_member_data in safe_getter(
            worker.source, 'message.new_chat_members', default=[], mode='DICT'):
        participant = get_from_Model(Participant, id=new_member_data['id'])
        if not participant:
            participant = user_registry.register_participant(new_member_data)
        gspd = get_from_Model(
            participant.groupspecificparticipantdata_set,
            participant_group=worker['participant_group'], _mode='direct')
        if not gspd:
            gspd = user_registry.register_groupspecificparticipantdata(
                participant=participant,
                participant_group=worker['participant_group'],
                joined=datetime.fromtimestamp(
                    worker['message']["date"], tz=timezone.get_current_timezone()),
            )
        new_members.append((participant, gspd))
    worker.source.new_members_models = new_members
    return new_members
