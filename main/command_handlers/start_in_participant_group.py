from main.models import BotBinding


def start_in_participant_group(worker):  # Won't work in new groups
    """ Will create bot bindings with a given group """
    binding = BotBinding(bot=worker.source.bot, participant_group=worker.source.participant_group)
    binding.save()
    worker.source.bot.send_message(
        worker.source.participant_group,
        "This participant_group is now bound with me, to break the connection, use /stop command.",
        reply_to_message_id=worker.source.message["message_id"],
    )
