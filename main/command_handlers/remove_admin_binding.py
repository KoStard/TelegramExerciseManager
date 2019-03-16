from main.universals import get_from_Model
from main.models import Participant


def remove_admin_binding(worker):
    """
    Will remove admin binding - has to be replied to that user's message.
    """
    if 'reply_to_message' not in worker.source.message:
        worker.answer_to_the_message("You have to reply to the user's message to promote him/her to admin.")
        return False
    user_data = worker.source.message['reply_to_message']['from']
    participant = get_from_Model(Participant, id=user_data['id'])
    if not participant:
        worker.answer_to_the_message(
            f"The user {user_data['first_name'] or user_data['username']} is not a participant.")
        return False
    gspd = get_from_Model(participant.groupspecificparticipantdata_set, _mode='direct',
                          participant_group=worker.source.administrator_page.participant_group)
    if not gspd:
        worker.answer_to_the_message(
            f"The user {participant.name} isn't registered in {worker.source.administrator_page.participant_group.title}.")
        return
    if not gspd.is_admin:
        worker.answer_to_the_message(
            f"The user {participant.name} is not an admin in the {worker.source.administrator_page.participant_group.title}.")
        return
    binding = get_from_Model(gspd.participantgroupbinding_set, _mode='direct', role__value='admin')
    if binding:
        binding.delete()
    worker.answer_to_the_message(f"{participant.name} is no longer an admin.")
