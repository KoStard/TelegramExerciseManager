from main.command_handlers import send_problem, answer_problem
from main.models import MessageInstance, ActionType
from datetime import datetime
from django.utils import timezone


def cycle(worker):
    if worker.command_argv:
        worker.answer_to_the_message("Cycle command can't get any arguments.")
        return

    # Registering message instance - before updating active problem
    if worker.source.command == 'cycle':
        MessageInstance.objects.create(
            action_type=ActionType.objects.get(value='problem_command'),
            date=datetime.fromtimestamp(
                worker['message']["date"],
                tz=timezone.get_current_timezone()),
            message_id=worker.source.message['message_id'],
            participant=worker.participant,
            participant_group=worker.participant_group,
            text=worker.source.raw_text,
            current_problem=worker.participant_group.activeProblem
        )
    
    answer_problem.answer_problem(worker)
    send_problem.send_problem(worker)
