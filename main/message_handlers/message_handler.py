"""
Handling Message and sending to other branches
"""
from main.message_handlers import user_message_handler, bot_message_handler


def handle_message(worker):
    if worker.source.message['from']['is_bot']:
        bot_message_handler.handle_message_from_bot(worker)
    else:
        user_message_handler.handle_message_from_user(worker)
