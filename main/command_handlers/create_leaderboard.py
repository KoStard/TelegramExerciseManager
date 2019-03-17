from main.models import TelegraphAccount
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator


def create_leaderboard(worker):
    """
    Will create leaderboard from admp
    """
    t_account: TelegraphAccount = TelegraphAccount.objects.first()
    if worker.source.administrator_page.participant_group.telegraphpage_set.count(
    ):
        worker.answer_to_the_message(
            f"Can't create leaderboard for a page if it already has one.\n"
            f"The link - {worker.source.administrator_page.participant_group.telegraphpage_set.last().url}"
        )
        return False
    worker.source.position_change = worker.source.position_change or {}
    d = worker.create_and_save_telegraph_page(
        t_account=t_account,
        title=' '.join(worker.source.command_argv)
        if worker.source.command_argv else ' '.join(
            worker.source.administrator_page.participant_group.title.split(' ')
            [:-1])  # Removing [MedStard] from the end
        + ' Leaderboard',
        content=worker.createGroupLeaderBoardForTelegraph(),
        participant_group=worker.source.administrator_page.participant_group)
    worker.answer_to_the_message(
        f"Created https://telegra.ph/{d.page_path} for {worker.source.administrator_page.participant_group.title}"
    )
    return d
