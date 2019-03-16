def stop_in_administrator_page(worker):
    """ Will remove administrator page """
    chat_id = worker.source.administrator_page.telegram_id
    worker.source.administrator_page.delete()
    worker.source.bot.send_message(
        chat_id,
        'This target is no longer an administrator page, so you won\'t get any log here anymore.',
        reply_to_message_id=worker.source.message['message_id'])
