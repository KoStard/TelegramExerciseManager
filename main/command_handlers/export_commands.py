from main.models import TelegramCommand
from django.db.models import Q


def export_commands(worker):
    # Exporting for the BotFather by default - maybe will add other modes in the future
    if not worker.command_argv:
        commands = TelegramCommand.objects.filter(
            Q(needs_superadmin=False) &
            (Q(in_participant_groups=True) |
             Q(in_unregistered=True))
        )
        worker.answer_to_the_message('\n'.join('{} - {}'.format(command.command, command.description) for command in
                        sorted(commands, key=lambda command: command.command)))
