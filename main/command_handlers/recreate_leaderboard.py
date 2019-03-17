from main.models import TelegraphAccount
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator


def recreate_leaderboard(worker):
    """
    Will recreate leaderboard for current admp's pg
    Will lead to some data loss - such as position changes
    """
    if not worker.source.administrator_page.participant_group.telegraphpage_set.count():
        worker.answer_to_the_message(
            "The group doesn't have any leaderboard telegraph page.")
        return False
    worker.source.position_change = worker.source.get('position_change') or {}
    t_page = worker.source.administrator_page.participant_group.telegraphpage_set.last()
    t_account = t_page.account
    page_controller = DynamicTelegraphPageCreator(t_account.access_token)
    page_controller.load_and_set_page(t_page.path, return_content=False)
    page_controller.update_page(
        content=worker.createGroupLeaderBoardForTelegraph())
    worker.answer_to_the_message(
        f"Updated https://telegra.ph/{page_controller.page_path} for {worker.source.administrator_page.participant_group.title}"
    )
    return page_controller
