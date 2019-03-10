"""
Here will be collected methods of user registry
"""

from main.models import Participant, GroupSpecificParticipantData
from main.universals import safe_getter


def register_participant(user_data) -> Participant:
    """
    Will register participant based on user_data
    """
    participant = Participant(
        username=safe_getter(user_data, 'username', mode='DICT'),
        first_name=safe_getter(user_data, 'first_name', mode='DICT'),
        last_name=safe_getter(user_data, 'last_name', mode='DICT'))
    participant.save()
    return participant


def register_groupspecificparticipantdata(
        **kwargs) -> GroupSpecificParticipantData:
    """
    Will register GroupSpecificParticipantData
    - participant
    - participant_group
    [Optional]
    - score
    - joined
    """
    gspd = GroupSpecificParticipantData(**kwargs)
    gspd.save()
    return gspd
