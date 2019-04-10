def recalculate_roles(worker):
    """
    Will recalculate roles of all members of the bound participant group
    """
    for gspd in worker.source.administrator_page.participant_group.groupspecificparticipantdata_set.all():
        gspd.recalculate_roles()
    worker.unilog("All roles are recalculated, to update the leaderboard run /recreate_leaderboard command.")
