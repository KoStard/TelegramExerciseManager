from main.universals import get_from_Model
from main.models import Participant, Role
from main.data_managers.user_registry import create_participantgroupbinding, register_groupspecificparticipantdata, \
    register_participant


def promote_to_admin(worker):
    """
    Will promote user to admin - has to be replied to that user's message.
    """
    if 'reply_to_message' not in worker.source.message:
        worker.answer_to_the_message("You have to reply to the user's message to promote him/her to admin.")
        return False
    user_data = worker.source.message['reply_to_message']['from']
    if user_data['is_bot']:
        worker.answer_to_the_message("Can't register bot as participant.")
        return False
    participant = get_from_Model(Participant, id=user_data['id'])
    if not participant:
        participant = register_participant(user_data)
    gspd = get_from_Model(participant.groupspecificparticipantdata_set, _mode='direct',
                          participant_group=worker.source.administrator_page.participant_group)
    if not gspd:
        gspd = register_groupspecificparticipantdata(
            participant=participant,
            participant_group=worker.source.administrator_page.participant_group
        )
    if gspd.is_admin:
        worker.answer_to_the_message(
            f"The user is already an admin in the {worker.source.administrator_page.participant_group.title}.")
        return
    create_participantgroupbinding(gspd, Role.objects.get(value='admin'))
    worker.answer_to_the_message(f"Congratulations, {participant.name} is now an admin.")
