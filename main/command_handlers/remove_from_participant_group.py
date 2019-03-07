def remove_from_participant_group(worker):
    """ Will remove bot binding with a given group """
    worker.source.bot.botbinding_set.objects.get(bot=worker.source.bot).delete()
    worker.source.bot.send_message(
        worker.source.participant_group,
        "The connection was successfully stopped.",
        reply_to_message_id=worker.source.message["message_id"],
    )
