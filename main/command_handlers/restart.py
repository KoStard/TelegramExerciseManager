from main.universals import update_and_restart


def restart(worker):
    """
    Will restart the script
    - Maybe will result to problems when in multi-bot mode, because will restart the program, while other
        bot's commands are being processed
    """
    worker.unilog("Has to restart")
    worker.add_to_post_processing_stack(worker.bot, update_and_restart)
