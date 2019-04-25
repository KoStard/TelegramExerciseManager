def root_test(worker):
    """ This is used for some root testings of the bot """
    worker.answer_to_the_message(worker.bot.get_chat_participants_count(worker.administrator_page.participant_group))
