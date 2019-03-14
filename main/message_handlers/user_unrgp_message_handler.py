"""
Will handle messages in unregistered groups from users
"""


def handle_message_from_unregistered_target(worker):
    """
    Will handle messages from unregistered groups/chats
    """
    if worker.source.is_superadmin:
        handle_message_from_superadmin_in_unregistered_group(worker)
    elif worker.source.message['chat']['type'] == 'private':
        # Will handle message from private chats
        handle_message_from_private_chat(worker)
    elif worker.source.message['chat']['type'] in ('group', 'supergroup'):
        # Will handle message from groups
        handle_message_from_unregistered_group(worker)


def handle_message_from_superadmin_in_unregistered_group(worker):
    """ Will handle message from superadmin
    that are not in the administrator page """
    if worker.command_model and worker.command_model.in_unregistered:
        worker.run_command()


def handle_message_from_private_chat(worker):
    """ Will handle message from private chat """
    worker['bot'].send_message(
        worker['message']['chat']['id'],
        "If you want to use this bot in your groups too, then connect with @KoStard.",
        reply_to_message_id=worker['message']['message_id'])


def handle_message_from_unregistered_group(worker):
    """ Will handle messages from groups """
    if worker.source.command:
        worker.source.bot.send_message(
            worker.source.message['chat']['id'],
            "If you want to use this bot in your groups too, then connect with @KoStard.",
            reply_to_message_id=worker.source.message['message_id'])
    else:
        pass  # When getting simple messages
