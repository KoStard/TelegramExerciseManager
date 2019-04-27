"""
Will handle messages from users in partisipant groups
"""

from main.message_handlers import user_pg_gor_sender, user_pg_register_new_members, user_pg_entities_handler, \
    user_pg_message_bindings_handler, user_pg_pgm_text_handler, user_pg_pgm_command_handler, \
    user_pg_message_validity_checker


def handle_message_from_participant_group(worker):
    """
    Will handle message from participant group
    """
    user_pg_gor_sender.get_or_register_message_sender_participant(worker)
    user_pg_gor_sender.get_or_register_groupspecificparticipantdata_of_active_participant(worker)
    user_pg_register_new_members.register_participant_group_new_members(worker)
    if user_pg_message_bindings_handler.has_message_bindings(worker):
        if worker.pg_adm_page:
            worker.bot.forward_message(
                from_group=worker.source.message['chat']['id'],
                to_group=worker.pg_adm_page,
                message_id=worker.source.message['message_id'],
            )
    status_checkers = (
        user_pg_entities_handler.handle_entities, user_pg_message_bindings_handler.handle_message_bindings,
        user_pg_message_validity_checker.check_message_validity)
    if all(checker(worker) for checker in status_checkers):  # Won't call all checkers if one of them returns False
        worker.unilog(worker.create_log_from_message())
        user_pg_pgm_text_handler.handle_pgm_text(worker)
        user_pg_pgm_command_handler.handle_pgm_commands(worker)
    else:
        worker.unilog(worker.create_log_from_message())
