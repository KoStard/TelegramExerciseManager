"""
Will handle commands from participant group members in participant groups
"""

from main.universals import get_from_Model
from main.models import ViolationType
from main.templates import command_rejection_message_template


def handle_pgm_commands(worker):
    """
    Will handle commands from participant_group message
    """
    if not worker['command']:
        return
    if worker.command_model:
        priority_level = worker.groupspecificparticipantdata.highest_role.priority_level
        if worker.command_model.needs_superadmin:  # Got superadmin commands in PG
            handle_superadmin_commands_in_pg(worker)  # Not checking permissions, just handling
        else:  # Got regular commands in PG
            if worker.is_from_superadmin or priority_level >= worker.command_model.minimal_priority_level:
                if worker.command_model.in_participant_groups:
                    worker.unilog("Command accepted")
                    accept_command_in_pg(worker)
                else:
                    worker.unilog("Command rejected")
                    reject_command_in_pg_because_of_source(worker)
            else:
                worker.unilog("Command rejected")
                reject_command_in_pg(worker)
    elif worker['command']:
        worker['bot'].send_message(
            worker['participant_group'],
            'Invalid command "{}"'.format(worker['command']),
            reply_to_message_id=worker['message']["message_id"],
        )


def handle_superadmin_commands_in_pg(worker):
    if worker.is_from_superadmin:
        if worker.command_model.in_participant_groups:
            worker.unilog("Command accepted")
            worker.run_command()
        else:
            worker.unilog("Command rejected")
            reject_command_in_pg_because_of_source(worker)
    else:
        worker.unilog("Command rejected")
        reject_command_in_pg(worker)


def reject_command_in_pg(worker):
    worker['bot'].send_message(
        worker['participant_group'],
        command_rejection_message_template.format(
            name=worker['participant'].name,
            command=worker['command'],
            highest_role=worker['groupspecificparticipantdata'].highest_role.name
        ),
        reply_to_message_id=worker['message']["message_id"],
    )
    worker['groupspecificparticipantdata'].create_violation(
        get_from_Model(ViolationType, value='command_low_permissions'), worker=worker)


def reject_command_in_pg_because_of_source(worker):
    worker.unilog("The command '{}' is not supposed to be used in the Participant Groups.".format(worker.command),
                  to_participant_group=True)


def accept_command_in_pg(worker):
    worker.run_command()
