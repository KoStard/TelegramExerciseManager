from main.universals import get_from_Model
from main.models import GroupType, ParticipantGroup, BotBinding
import logging


def register_participant_group(worker):
    """ Will register chat as a participant group """
    chat = worker.source.message.get("chat")
    tp = get_from_Model(GroupType, name=chat['type'])
    if not chat:
        logging.info("Can't get chat to register.")
        pass
    participant_group = get_from_Model(
        ParticipantGroup, telegram_id=chat['id'])
    if participant_group:
        worker.source.bot.send_message(
            participant_group,
            "This group is already registered.",
            reply_to_message_id=worker.source.message['message_id']
        )  # Maybe add reference to the documentation with this message
    elif not tp:
        worker.source.bot.send_message(
            chat['id'],
            "Unknown type of group, to improve this connect with @KoStard.",
            reply_to_message_id=worker.source.message['message_id'])
    else:
        participant_group = ParticipantGroup(
            telegram_id=chat['id'],
            username=chat.get('username'),
            title=chat.get('title'),
            type=tp)
        participant_group.save()
        binding = BotBinding(bot=worker.source.bot, participant_group=participant_group)
        binding.save()
        worker.source.bot.send_message(
            participant_group,
            """This group is now registered and a binding is created,\
so now the bot will listen to your commands.""",
            reply_to_message_id=worker.source.message['message_id'])
