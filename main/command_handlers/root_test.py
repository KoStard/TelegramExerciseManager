def root_test(worker):
    """ This is used for some root testings of the bot """
    ### Now will be used for image sending test
    try:
        worker.source.bot.send_image(
            worker.source.administrator_page,
            open('../media/images/Photos/image005.png', 'rb'),
            reply_to_message_id=worker.source.message['message_id']
        )  # Is working, so the bug with image sending is solved.
    except Exception as e:
        print(e)
        worker.unilog("Can't send image in root_test")
