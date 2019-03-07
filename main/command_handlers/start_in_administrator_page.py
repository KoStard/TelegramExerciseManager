from main.models import AdministratorPage, GroupType


def start_in_administrator_page(worker):
    """ Will save administrator page """
    administrator_page = AdministratorPage(
        telegram_id=worker.source.message["chat"]["id"],
        username=worker.source.message["chat"].get("username"),
        title=worker.source.message["chat"].get("title"),
        type=(GroupType.objects.filter(name=worker.source.message["chat"].get("type"))
              or [None])[0],
    )
    administrator_page.save()
    worker.source.bot.send_message(
        administrator_page,
        "Congratulations, this group is now registered as an administrator page.",
        reply_to_message_id=worker.source.message['message_id'])
