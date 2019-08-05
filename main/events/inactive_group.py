from django.utils import timezone
from main.models import MessageInstance, ActionType
from datetime import datetime


def check(worker):
    curr = timezone.now()
    threshold = 3 * 3600  # 3 hours
    for pg in (e.participant_group for e in worker.bot.botbinding_set.all()):
        last_message_instance = pg.messageinstance_set.last()
        if pg.activeProblem and (curr - last_message_instance.date).seconds > threshold:
            if last_message_instance.action_type.value == 'bot_inactivity_notification':
                last_message_instance.remove_message(worker)
                last_message_instance.delete()
            text = "Hey, don't miss your chance to answer the problem "\
                "and take a higher position in the leaderboard!"
            notification_message = worker.bot.send_message(
                pg, text)[0]
            MessageInstance.objects.create(
                action_type=ActionType.objects.get(
                    value='bot_inactivity_notification'),
                date=datetime.fromtimestamp(
                    notification_message["date"],
                    tz=timezone.get_current_timezone()),
                message_id=notification_message['message_id'],
                participant=None,
                participant_group=pg,
                text=text,
                current_problem=pg.activeProblem
            )
