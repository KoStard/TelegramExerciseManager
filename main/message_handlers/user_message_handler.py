"""
Will handle message from user
"""

from main.universals import get_from_Model
from main.models import TelegramCommand, ParticipantGroup, SuperAdmin, AdministratorPage
from main.message_handlers import user_pg_message_handler, user_admp_message_handler, user_unrgp_message_handler


def handle_message_from_user(worker):
    """ Handling message from user
    [Saving]
    - text
    - command
    - participant_group
    - is_superadmin
    - is_administrator_page
    - administrator_page
    """
    worker.source.raw_text = worker.source.message.get("text")

    # This won't work with multiargumental commands
    worker.source.command = worker.source.raw_text[1:].split(" ")[0].split('@')[0] if worker.source.raw_text and \
                                                                                      worker.source.raw_text[
                                                                                          0] == '/' else ''

    if worker.source.command:
        worker.source.command_model = get_from_Model(
            TelegramCommand, command=worker.command)
    else:
        worker.source.command_model = None

    worker.source.text = worker.source.raw_text if not worker.source.command else None

    # Checking if the group is registered
    worker.source.participant_group = get_from_Model(
        ParticipantGroup, telegram_id=worker.source.message["chat"]["id"])

    if worker.source.participant_group:
        worker.source.pg_adm_page = worker.source.participant_group.get_administrator_page()

    # Checking if is a superadmin
    worker.source.is_superadmin = not not SuperAdmin.objects.filter(
        user__id=worker.source.message['from']['id'])

    # Checking if in an administrator page
    worker.source.administrator_page = get_from_Model(
        AdministratorPage, telegram_id=worker.source.message['chat']['id'])
    worker.source.is_administrator_page = not not worker.source.administrator_page

    if worker.participant_group:
        # If the participant group is already registered
        user_pg_message_handler.handle_message_from_participant_group(worker)
    elif worker.source.is_administrator_page:
        # If the message is in the administrator page
        user_admp_message_handler.handle_message_from_administrator_page(
            worker)
    elif worker.source.is_superadmin or worker.source.message['chat'][
            'type'] in ('private', 'group', 'supergroup'):
        # If the user if superadmin but is sending a message not in a registered group
        user_unrgp_message_handler.handle_message_from_unregistered_target(
            worker)
    else:
        print("Don't know what to do... :/")
