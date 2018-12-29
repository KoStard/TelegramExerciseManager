from main.models import *
from main.universals import (
    get_request,
    configure_logging,
)
from time import sleep
from datetime import datetime
import logging
# configure_logging()


def participant_answering(participant, group, problem, variant):
    is_right = False
    variant = variant.lower()
    try:
        group_specific_participant_data = participant.groupspecificparticipantdata_set.get(
            group=group)
    except GroupSpecificParticipantData.DoesNotExist:
        group_specific_participant_data = GroupSpecificParticipantData(**{
            'participant': participant,
            'group': group,
            'score': 0,
        })
        group_specific_participant_data.save()
    right_answers_count = len(problem.answer_set.filter(
        right=True, processed=False, group_specific_participant_data__group=group))  # Getting right answers only from current group
    if variant == problem.right_variant.lower():
        print("Right answer from {} N{}".format(
            participant, right_answers_count))
        is_right = True
    else:
        print("Wrong answer from {} - Right answers {}".format(participant,
                                                               right_answers_count))
    if not problem.answer_set.filter(group_specific_participant_data=group_specific_participant_data, processed=False):
        answer = Answer(**{
            'problem': problem,
            'answer': variant,
            'right': is_right,
            'processed': False,
            'group_specific_participant_data': group_specific_participant_data,
        })
        answer.save()


def update_bot(bot: Bot):
    """ Will get bot updates """
    url = bot.base_url + 'getUpdates?' + \
        ('offset={}'.format(bot.offset) if bot.offset else '')
    resp = get_request(url)
    bot.last_updated = datetime.now()
    bot.save()
    for update in resp:
        message = update.get('message')
        if message and not message['from']['is_bot']:
            print('{} [{}] -> {}'.format(message['from'].get('first_name') or message['from'].get('username') or
                                         message['from'].get('last_name'), bot, message.get('text') or "|UNKNOWN|"))
            logging.info('{}| {} [{}] -> {}'.format(datetime.now(), message['from'].get('first_name') or message['from'].get('username') or
                                                    message['from'].get('last_name'), bot, message.get('text') or message))
            try:
                group = Group.objects.get(telegram_id=message['chat']['id'])
            except Group.DoesNotExist:
                bot.send_message(message['chat']['id'],
                                 'Hi, if you want to use this bot in your groups too, then contact with @KoStard')
                continue

            if message.get('new_chat_members'):
                for new_chat_member_data in message['new_chat_members']:
                    if new_chat_member_data['is_bot'] or Participant.objects.filter(pk=new_chat_member_data['id']):
                        continue
                    Participant(**{
                        'id': new_chat_member_data['id'],
                        'username': new_chat_member_data.get('username'),
                        'first_name': new_chat_member_data.get('first_name'),
                        'last_name': new_chat_member_data.get('last_name'),
                        'sum_score': 0,
                    }).save()
            try:
                participant = Participant.objects.get(pk=message['from']['id'])
            except Participant.DoesNotExist:
                participant = Participant(**{
                    'id': message['from']['id'],
                    'username': message['from'].get('username'),
                    'first_name': message['from'].get('first_name'),
                    'last_name': message['from'].get('last_name'),
                    'sum_score': 0,
                })
                participant.save()
            text = message.get('text')
            if text:
                if len(text) == 1 and (
                        ord(text) in range(ord('a'), ord('e') + 1) or ord(text) in range(ord('A'), ord('E') + 1)):
                    if group.activeProblem and BotBinding.objects.filter(bot=bot, group=group):
                        participant_answering(
                            participant, group, group.activeProblem, text)
                elif text[0] == '/':
                    command = text[1:].split(' ')[0]
                    if command in available_commands:
                        participant_group_bindings = ParticipantGroupBinding.objects.filter(participant=participant,
                                                                                            group=group)
                        if participant_group_bindings:
                            max_priority_role = \
                                sorted(participant_group_bindings, key=lambda binding: binding.role.priority_level)[
                                    -1].role
                        else:
                            max_priority_role = Role.objects.get(
                                value='participant')
                        if max_priority_role.priority_level >= available_commands[command][1]:
                            if available_commands[command][2]:
                                if not BotBinding.objects.filter(bot=bot, group=group):
                                    bot.send_message(group,
                                                     'Hi, if you want to use this bot in '
                                                     'your groups too, then contact with @KoStard')
                                    return
                            available_commands[command][0](
                                bot, group, text, message)
                        else:
                            bot.send_message(group,
                                             "Sorry dear {}, your role \"{}\" is not granted to use this command.".format(
                                                 participant, max_priority_role.name))
                    else:
                        bot.send_message(
                            group, 'Invalid command "{}"'.format(command))
            participant.save()
        bot.offset = update['update_id'] + 1
        bot.save()


def send_problem(bot: Bot, group: Group, text, message):
    index = int(text.split()[1])
    try:
        problem = group.activeSubject.problem_set.get(index=index)
    except Problem.DoesNotExist:
        bot.send_message(group, 'Invalid problem number "{}".')
    else:
        form_resp = bot.send_message(group, str(problem))
        logging.info("Sending problem {}".format(problem.index))
        if problem.img and form_resp:
            bot.send_image(group, open('media/'+problem.img.name,
                                       'rb'), reply_to_message_id=form_resp[0].get('message_id'), caption='Image of problem N{}.'.format(problem.index))
            logging.info("Sending image for problem {}".format(problem.index))
        group.activeSubject = problem.subject
        group.activeProblem = problem
        group.save()


def answer_problem(bot, group, text, message):
    if not group.activeProblem and len(text.split()) <= 1:
        bot.send_message(group, "There is no active problem for this group.")
        return
    problem = group.activeProblem
    if len(text.split()) > 1:
        index = int(text.split()[1])
        if problem and index > problem.index:
            bot.send_message(
                group, "You can't send new problem's answer without opening it.")
            return
        elif not problem or index < problem.index:
            try:
                problem = group.activeSubject.problem_set.get(index=index)
            except Problem.DoesNotExist:
                bot.send_message(group, 'Invalid problem number {}.')
            else:
                bot.send_message(group, problem.get_answer())
            return
    bot.send_message(group, problem.get_answer())
    bot.send_message(group, problem.close(group))
    group.activeProblem = None
    group.save()


def start_in_group(bot, group, text, message):
    binding = BotBinding(bot=bot, group=group)
    binding.save()
    bot.send_message(
        group, "This group is now bound with me, to break the connection, use /stop command.")


def remove_from_group(bot, group, text, message):
    bot.botbinding_set.objects.get(bot=bot).delete()
    bot.send_message(group, "The connection was successfully stopped.")


def add_subject(bot, group, text, message):
    pass


def select_subject(bot, group, text, message):
    pass


def finish_subject(bot, group, text, message):
    pass


def get_score(bot, group, text, message):
    participant = Participant.objects.filter(pk=message['from']['id'])
    if participant:
        participant = participant[0]
        specific = GroupSpecificParticipantData.objects.filter(
            participant=participant, group=group)
        if specific:
            specific = specific[0]
            bot.send_message(group, "{}'s score is {}".format(
                str(participant), specific.score))


# (function, min_priority_level, needs_binding)
available_commands = {
    'send': (send_problem, 6, True),
    'answer': (answer_problem, 6, True),
    'start': (start_in_group, 8, False),
    'stop': (remove_from_group, 8, True),
    'add_subject': (add_subject, 9, True),
    'select_subject': (select_subject, 9, True),
    'finish_subject': (finish_subject, 9, True),
    'score': (get_score, 0, True),
}
