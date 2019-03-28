"""
Will handle messages from administrator pages
"""

from main.universals import get_from_Model, safe_getter
from main.models import Participant, Role
from main.templates import command_rejection_message_template


def handle_message_from_administrator_page(worker):
    """ Will handle message from administrator page
    + superadmins """
    if not worker.command:
        return  # Just text
    if worker.command_model:
        get_message_sender_participant_from_administrator_page(worker)
        if not worker.participant:
            worker.unilog("Unknown user in the administrator page.")
            return
        priority_level = -1
        # if not worker.is_from_superadmin and not worker.command_model.needs_superadmin:
        get_groupspecificparticipantdata_of_active_participant_from_administrator_page(
            worker)
        priority_level = worker.groupspecificparticipantdata.highest_role.priority_level
        if worker.is_from_superadmin or (
                not worker.command_model.needs_superadmin and
                priority_level >= worker.command_model.minimal_priority_level):
            if not worker.command_model.in_administrator_pages:
                # worker.unilog("Command rejected")
                reject_command_in_administrator_pages_because_of_source(worker)
                return
            if worker.command_model.in_admp_needs_bound_participant_group and not worker.administrator_page.participant_group:
                reject_command_in_administrator_pages_because_of_no_pg(worker)
                return
            # worker.unilog("Command accepted")
            worker.run_command()
        else:
            # worker.unilog("Command rejected")
            reject_command_in_administrator_page(worker)
    else:
        worker['bot'].send_message(
            worker['administrator_page'],
            "Invalid command.",
            reply_to_message_id=worker['message']['message_id'])


def get_message_sender_participant_from_administrator_page(worker):
    """
    Will get participant from administrator page message
    """
    if worker.source.get('message'):
        participant = get_from_Model(
            Participant, id=worker['message']['from']['id'])
        if not participant:
            worker.source.participant = None
            worker.source.is_from_superadmin = False
            print("Can't find participant {}".format(
                worker.message['from']['first_name']
                or worker.message['from']['username']
                or worker.message['from']['last_name']))
            return
        worker.source.participant = participant
        worker.source.is_from_superadmin = not not safe_getter(
            worker.participant, 'superadmin')
        return participant
    else:
        worker.source.participant = None
        worker.source.is_from_superadmin = False
        raise ValueError("INVALID MESSAGE DATA")


def get_groupspecificparticipantdata_of_active_participant_from_administrator_page(
        worker):
    """
    Will get groupspecificparticipantdata from administrator page and participant
    """
    worker.groupspecificparticipantdata = get_from_Model(
        worker.participant.groupspecificparticipantdata_set,
        _mode='direct',
        participant_group__administratorpage=worker.administrator_page)


def reject_command_in_administrator_pages_because_of_source(worker):
    worker.unilog(
        "The command '{}' is not supposed to be used in the Administrator Pages."
        .format(worker.command))


def reject_command_in_administrator_page(worker):
    worker['bot'].send_message(
        worker.administrator_page,
        command_rejection_message_template.format(
            name=worker['participant'].name,
            command=worker['command'],
            highest_role=worker['groupspecificparticipantdata'].highest_role.
            name if worker['groupspecificparticipantdata'] else
            Role.objects.get(value='guest').name),
        reply_to_message_id=worker['message']["message_id"],
    )


def reject_command_in_administrator_pages_because_of_no_pg(worker):
    worker.unilog(
        "The command '{}' is not supposed to be used in the no-participant-group Administrator Pages."
        .format(worker.command))
