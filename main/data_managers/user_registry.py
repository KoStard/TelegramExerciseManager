"""
Here will be collected methods of user registry
"""

from main.models import Participant, GroupSpecificParticipantData, Role, ParticipantGroup, ParticipantGroupBinding, \
    ParticipantGroupMembersCountRegistry
from main.universals import safe_getter
from django.utils import timezone


def register_participant(user_data) -> Participant:
    """
    Will register participant based on user_data
    """
    participant = Participant(
        id=user_data['id'],
        username=safe_getter(user_data, 'username', mode='DICT'),
        first_name=safe_getter(user_data, 'first_name', mode='DICT'),
        last_name=safe_getter(user_data, 'last_name', mode='DICT'))
    participant.save()
    return participant


def register_groupspecificparticipantdata(**kwargs
                                          ) -> GroupSpecificParticipantData:
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


def create_participantgroupbinding(gspd: GroupSpecificParticipantData,
                                   role: Role) -> ParticipantGroupBinding:
    return ParticipantGroupBinding.objects.create(
        groupspecificparticipantdata=gspd, role=role)


def register_current_participant_group_members_count(worker):
    current_count = worker.bot.get_chat_participants_count(worker.active_pg)
    # Participant-Group members count
    pgmc = ParticipantGroupMembersCountRegistry.objects.create(participant_group=worker.active_pg,
                                                               current_count=current_count, date=timezone.now())
    return pgmc
