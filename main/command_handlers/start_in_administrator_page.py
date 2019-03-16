from main.models import AdministratorPage, GroupType, ParticipantGroup


def start_in_administrator_page(worker):
    """ Will save administrator page """
    pg = None
    if worker.source.command_argv:
        if worker.source.command_argv[0].isdecimal():
            index = int(worker.source.command_argv[0]) - 1
            pgs = ParticipantGroup.objects.all()
            if 0 <= index < len(pgs):
                pg = pgs[index]
    if pg.get_administrator_page():
        worker.source.bot.send_message(
            worker.source.message['chat']['id'],
            f"You can't register this group as an administrator page for {pg.title}, because it already has one.",
            reply_to_message_id=worker.source.message['message_id']
        )
        return False
    administrator_page = AdministratorPage(
        telegram_id=worker.source.message["chat"]["id"],
        username=worker.source.message["chat"].get("username"),
        title=worker.source.message["chat"].get("title"),
        type=(GroupType.objects.filter(name=worker.source.message["chat"].get("type"))
              or [None])[0],
        participant_group=pg
    )
    administrator_page.save()
    worker.source.bot.send_message(
        administrator_page,
        ("Congratulations, this group is now registered as an administrator page" +
         (f" for {pg.title}" if pg else "") +
         "."
         ),
        reply_to_message_id=worker.source.message['message_id'])
    return True
