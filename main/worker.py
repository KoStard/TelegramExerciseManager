from main.models import *
from main.universals import get_response, configure_logging, safe_getter, get_from_Model, update_and_restart
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator
from django.utils import timezone
from time import sleep
from datetime import datetime
import logging
from functools import wraps

"""
Will contain here whole update data in a dict
- last element is the dict
- won't work with multiple bots - multiple threads will work on same stack element
"""
DATA_STACK = []


def sourced(func):
    @wraps(func)
    def inner(*args, from_args=False, **kwargs):  # args are not used, will stay it here while integrating with commands
        return func(DATA_STACK[-1] if not from_args else kwargs)

    return inner


# configure_logging()


def adm_log(bot: Bot, participant_group: ParticipantGroup or AdministratorPage, message: str):
    """ Will log to the administrator page if available """
    if hasattr(participant_group, 'administratorpage'):
        bot.send_message(participant_group.administratorpage, message)
    elif isinstance(participant_group, AdministratorPage):
        bot.send_message(participant_group, message)


AVAILABLE_ENTITIES = {
    "mention": -1,
    "hashtag": 1,
    "cashtag": 0,
    "bot_command": 0,
    "url": 2,
    "email": 1,
    "phone_number": 0,
    "bold": 0,
    "italic": 0,
    "code": 0,
    "pre": 0,
    "text_link": 3,
    "text_mention": -1,
}


@sourced
def check_entities(source):
    """ Will check message for entities and check participant's permissions to use them """
    resp = {"status": True, "unknown": False}
    priority_level = source[
        'groupspecificparticipantdata'].highest_role.priority_level
    for entity in source['entities']:
        entity = entity["type"]
        if entity not in AVAILABLE_ENTITIES:
            resp["status"] = False
            resp["cause"] = "Unknown entity {}".format(entity)
            resp["unknown"] = True
            break
        if AVAILABLE_ENTITIES[entity] > priority_level:
            resp["status"] = False
            resp[
                "cause"] = "{} entity is not allowed for users with priority level lower than {}".format(
                entity, AVAILABLE_ENTITIES[entity])
            break
    return resp


AVAILABLE_MESSAGE_BINDINGS = {
    "document": 0,
    "sticker": 0,
    "photo": 1,
    "audio": 2,
    "animation": 2,
    "voice": 2,
    "game": 3,
    "video": 3,
    "video_note": 3,
}


@sourced
def check_message_bindings(source):
    """ Will check message for bindings and check participant's permissions to use them """
    resp = {"status": True, "unknown": False}
    priority_level = source[
        'groupspecificparticipantdata'].highest_role.priority_level
    for message_binding in AVAILABLE_MESSAGE_BINDINGS:
        if message_binding in source['message'] and AVAILABLE_MESSAGE_BINDINGS[
            message_binding] > priority_level:
            if resp["status"]: resp["status"] = False
            if "cause" not in resp:
                resp["cause"] = []
            resp["cause"].append(
                "\"{}\" message binding is not allowed for users with priority level lower than {}"
                    .format(message_binding,
                            AVAILABLE_MESSAGE_BINDINGS[message_binding]))
    return resp


def save_to_data_stack(**kwargs):
    for arg in kwargs:
        DATA_STACK[-1][arg] = kwargs[arg]


def get_from_data_stack(**kwargs):
    if len(kwargs) > 1: return [DATA_STACK[-1][arg] for arg in kwargs]
    return DATA_STACK[-1][kwargs.values[0]]


def get_updates(bot: Bot, *, update_last_updated=True, timeout=60):
    """ Will return bot updates """
    url = bot.base_url + "getUpdates"  # The URL of getting bot updates
    updates = get_response(
        url,
        payload={
            'offset': bot.offset or "",  # Setting offset
            'timeout':
                timeout  # Setting timeout to delay empty updates handling
        })
    if update_last_updated:
        bot.last_updated = timezone.now()
        bot.save()
    return updates


def handle_update(bot, update, *, catch_exceptions=False) -> bool:
    """ Handling Update
    - True -> the process is finished normal
    - False -> catched exception
    - exception -> when exception was raised, but catch_exception is False

    Adding {update, message, bot} to the DATA_STACK
    """
    message = update.get('message')
    DATA_STACK.append({
        'update': update,
        'message': message,
        'bot': bot
    })  # Adding the dictionary for this update
    catched_exception = False
    if message:
        try:
            handle_message(bot, message)
        except Exception as exception:
            if catch_exceptions:
                catched_exception = True
                return False
            else:
                DATA_STACK.pop()
                raise exception
    DATA_STACK.pop()
    return True


@sourced
def create_log_from_message(source) -> str:
    """ Creating log from Telegram message """
    pr_m = ''  # Priority marker
    if source['groupspecificparticipantdata'].is_admin:
        pr_m = '🛡️'
    else:
        pr_m = '⭐' * max(source['groupspecificparticipantdata'].highest_standard_role_binding.role.priority_level, 0)

    if pr_m:
        pr_m += ' '

    name = source['participant'].name
    data = (
                   (source['raw_text'] or '') +
                   ('' if not source['entities'] else
                    '\nFound entities: ' + ', '.join(entity['type']
                                                     for entity in source['entities']))
           ) or ', '.join(
        message_binding for message_binding in AVAILABLE_MESSAGE_BINDINGS
        if message_binding in source['message']
    ) or (("New chat member" if len(source['message']['new_chat_members']) == 1
                                and source['message']['new_chat_members'][0]['id'] ==
                                source['message']['from']['id'] else 'Invited {}'.format(', '.join(
        user['first_name'] or user['last_name'] or user['username']
        for user in source['message'].get('new_chat_members'))))
          if 'new_chat_members' in source['message'] else '')
    result = f"{pr_m}{name} -> {data}"
    return result


def unilog(log: str) -> None:
    """ Will log to the:
    - stdout
    - logging
    - adm_page
    """
    print(log)  # Logging to stdout
    logging.info(f'{timezone.now()} | {log}')  # Logging to logs file
    adm_log(DATA_STACK[-1]['bot'], DATA_STACK[-1]['participant_group']
            or DATA_STACK[-1]['administrator_page'],
            log)  # Logging to administrator page


def register_participant(user_data) -> Participant:
    """
    Will register participant based on user_data
    """
    participant = Participant(
        username=safe_getter(user_data, 'username', mode='DICT'),
        first_name=safe_getter(user_data, 'first_name', mode='DICT'),
        last_name=safe_getter(user_data, 'last_name', mode='DICT'))
    participant.save()
    return participant


def register_groupspecificparticipantdata(
        **kwargs) -> GroupSpecificParticipantData:
    """
    Will register GroupSpecificParticipantData
    - participant
    - participant_group
    [Optional]
    - score
    - joined
    """
    gspd = GroupSpecificParticipantData(**kwargs)
    gspd.save()
    return gspd


@sourced
def get_or_register_message_sender_participant(source) -> Participant:
    """
    Will get if registered or register message sender as a participant
    """
    if safe_getter(source, 'message.from', mode='DICT'):
        participant = get_from_Model(
            Participant, id=source['message']['from']['id'])
        if not participant:
            participant = register_participant(source['message']['from'])
        save_to_data_stack(participant=participant)
        return participant
    else:
        save_to_data_stack(participant=None)
        raise ValueError("INVALID MESSAGE DATA")


@sourced
def get_or_register_groupspecificparticipantdata_of_active_participant(
        source) -> GroupSpecificParticipantData:
    """
    Will get if registered or register participant in active participant_group
    """
    if source['participant_group'] and source['participant']:
        gspd = get_from_Model(
            source['participant'].groupspecificparticipantdata_set,
            participant_group=source['participant_group'], _mode='direct')
        if not gspd:
            gspd = register_groupspecificparticipantdata(
                participant=source['participant'],
                participant_group=source['participant_group'])
        save_to_data_stack(groupspecificparticipantdata=gspd)
        return gspd
    else:
        save_to_data_stack(groupspecificparticipantdata=None)
        raise ValueError(
            "INVALID DATA IN get_or_register_groupspecificparticipantdata_of_active_participant"
        )


@sourced
def register_participant_group_new_members(source) -> list:
    """
    Will register all participant group new members
    """
    new_members = []
    for new_member_data in safe_getter(
            source, 'message.new_chat_members', default=[], mode='DICT'):
        participant = get_from_Model(Participant, id=new_member_data['id'])
        if not participant:
            participant = register_participant(new_member_data)
        gspd = get_from_Model(
            participant.groupspecificparticipantdata_set,
            participant_group=source['participant_group'], _mode='direct')
        if not gspd:
            gspd = register_groupspecificparticipantdata(
                participant=participant,
                participant_group=source['participant_group'],
                joined=datetime.fromtimestamp(
                    source['message']["date"], tz=timezone.get_current_timezone()),
            )
        new_members.append((participant, gspd))
    save_to_data_stack(new_members_models=new_members)
    return new_members


@sourced
def handle_entities(source) -> bool:
    """ Will handle entities from source's message """
    entities = safe_getter(source, 'message.entities', mode='dict', default=[])
    save_to_data_stack(entities=entities)
    entities_check_response = check_entities()
    save_to_data_stack(entities_check_response=entities_check_response)
    logging.info("Found Entity: " + str(entities_check_response))
    if not entities_check_response["status"]:
        if not entities_check_response["unknown"]:
            # Sending answer message to the message with restricted entities
            source['bot'].send_message(
                source['participant_group'],
                "Dear {}, your message will be removed, because {}.\nYou have [{}] roles.\
                \nFor more information contact with @KoStard".format(
                    source['participant'].name,
                    entities_check_response["cause"],
                    ", ".join("{} - {}".format(
                        participantgroupbinding.role.name,
                        participantgroupbinding.role.priority_level,
                    ) for participantgroupbinding in
                              source['groupspecificparticipantdata'].
                              participantgroupbinding_set.all())
                    or '-',
                ),
                reply_to_message_id=source['message']["message_id"],
            )
            # Removing message with restricted entities
            source['bot'].delete_message(source['participant_group'],
                                         source['message']["message_id"])
            # Creating violation
            source['groupspecificparticipantdata'].create_violation(
                get_from_Model(
                    ViolationType,
                    value='message_entity_low_permissions'),
                datetime.fromtimestamp(
                    source['message']["date"],
                    tz=timezone.get_current_timezone()))
            return False
    return True


@sourced
def handle_message_bindings(source) -> bool:
    message_bindings_check_response = check_message_bindings()
    if not message_bindings_check_response["status"]:
        logging.info(message_bindings_check_response["cause"])
        if not message_bindings_check_response["unknown"]:
            source['bot'].send_message(
                source['participant_group'],
                "Dear {}, your message will be removed, because {}.\nYou have [{}] roles.\
                \nFor more information contact with @KoStard".format(
                    source['participant'].name,
                    ', '.join(message_bindings_check_response["cause"]),
                    ", ".join("{} - {}".format(
                        participantgroupbinding.role.name,
                        participantgroupbinding.role.priority_level,
                    ) for participantgroupbinding in
                              source['groupspecificparticipantdata'].
                              participantgroupbinding_set.all()),
                ),
                reply_to_message_id=source['message']["message_id"],
            )
            source['bot'].delete_message(source['participant_group'],
                                         source['message']["message_id"])
            source['groupspecificparticipantdata'].create_violation(
                get_from_Model(
                    ViolationType,
                    value='message_binding_low_permissions'))
            return False
    return True


@sourced
def handle_answer_change(source):
    """
    Catching when participant is trying to change the answer
    """
    if not source.get('bot') or not source.get('message'):
        return
    if source['old_answer'].answer.upper() == source['variant'].upper():
        # Sending same answer again
        unilog("{} is trying to answer {} again".format(
            source['participant'], source['variant']))
        source['bot'].delete_message(source['participant_group'],
                                     source['message']['message_id'])
    else:
        unilog("{} is trying to change answer {} to {}".format(
            source['participant'], source['old_answer'].answer,
            source['variant']))
        source['bot'].send_message(
            source['participant_group'],
            'Dear {}, you can\'t change your answer.'.format(
                source['participant'].name),
            reply_to_message_id=source['message']['message_id'])


@sourced
def accept_answer(source) -> Answer:
    """
    Accepting answer - right or wrong
    """
    if source['variant'] == source['participant_group'].activeProblem.right_variant.upper():
        print("Right answer from {} N{}".format(
            source['participant'],
            len(
                source['participant_group'].activeProblem.answer_set.filter(
                    right=True,
                    processed=False,
                    group_specific_participant_data__participant_group=
                    source['participant_group'])) + 1))
    else:
        print("Wrong answer from {} - Right answers {}".format(
            source['participant'],
            len(
                source['participant_group'].activeProblem.answer_set.filter(
                    right=True,
                    processed=False,
                    group_specific_participant_data__participant_group=source[
                        'participant_group']))))
    answer = Answer(
        problem=source['participant_group'].activeProblem,
        answer=source['variant'],
        right=source['variant'] == source['participant_group'].activeProblem.right_variant.upper(),
        processed=False,
        group_specific_participant_data=source['groupspecificparticipantdata'],
        date=timezone.now(),
    )
    answer.save()
    return answer


@sourced
def handle_answers_from_testing_bots(source):
    """
    Will handle answers from testing bots
    """
    unilog("Answer from testing bot's controlling groups")


@sourced
def handle_answer(source):
    """
    Will handle participant answers
    """
    if not source['participant_group'].activeProblem:
        print(f"There is no active problem in {source['participant_group']}")
        return False
    old_answer = get_from_Model(
        source['participant_group'].activeProblem.answer_set,
        group_specific_participant_data=source[
            'groupspecificparticipantdata'],
        processed=False,
        _mode='direct')
    save_to_data_stack(old_answer=old_answer)
    if old_answer:
        handle_answer_change()
    elif source['bot'].for_testing:
        handle_answers_from_testing_bots()
    else:
        accept_answer()


@sourced
def handle_pgm_text(source):
    """
    Will handle text from participant_group message
    """
    if not source['text']:
        return  # There is no text in the message
    if len(source['text']) == 1 and source['text'].upper() in ('A', 'B', 'C', 'D', 'E'):
        save_to_data_stack(variant=source['text'].upper())
        handle_answer()
    else:
        pass  # Just regular message in participant group


@sourced
def handle_superadmin_commands_in_pg(source):
    available_commands[
        source['command']][0](  # These functions will becose sourced too soon
        source['bot'], source['participant_group'], source['raw_text'],
        source['message'])


@sourced
def accept_command_in_pg(source):
    available_commands[source['command']][0](  # These functions will become sourced too soon
        source['bot'], source['participant_group'], source['raw_text'],
        source['message'])


@sourced
def reject_command_in_pg(source):
    source['bot'].send_message(
        source['participant_group'],
        'Sorry dear {}, you don\'t have permission to use \
                command {} - your highest role is "{}".'.format(
            source['participant'], source['command'],
            source['groupspecificparticipantdata'].highest_role.name),
        reply_to_message_id=source['message']["message_id"],
    )
    source['groupspecificparticipantdata'].create_violation(
        get_from_Model(ViolationType, value='command_low_permissions'))


@sourced
def handle_pgm_commands(source):
    """
    Will handle commands from participant_group message
    """
    if not source['command']:
        return
    if source['command'] in available_commands:
        priority_level = source[
            'groupspecificparticipantdata'].highest_role.priority_level
        if (available_commands[source['command']][1] == 'superadmin'
                and safe_getter(source['participant'], 'superadmin')
        ):
            handle_superadmin_commands_in_pg()
        elif (safe_getter(source['participant'], 'superadmin')
              or priority_level >= available_commands[source['command']][1]
        ) and source['command'] != 'status':
            accept_command_in_pg()
        else:
            reject_command_in_pg()
    elif source['command']:
        source['bot'].send_message(
            source['participant_group'],
            'Invalid command "{}"'.format(source['command']),
            reply_to_message_id=source['message']["message_id"],
        )


@sourced
def handle_message_from_participant_group(source):
    """
    Will handle message from participant group
    """
    get_or_register_message_sender_participant()
    get_or_register_groupspecificparticipantdata_of_active_participant()
    register_participant_group_new_members()
    if handle_entities() and handle_message_bindings():
        unilog(create_log_from_message())
        handle_pgm_text()
        handle_pgm_commands()
    else:
        unilog(create_log_from_message())


@sourced
def handle_message_from_administrator_page(source):
    """ Will handle message from administrator page
    + superadmins """
    if not source['command']:
        return  # Just text
    if source['command'] in available_commands:
        if (
                available_commands[source['command']][1] == 'superadmin'
                or source['command'] == 'status'
        ) and available_commands[source['command']][2]:
            available_commands[source['command']][0](
                source['bot'], source['administrator_page'],
                source['raw_text'], source['message'])
        else:
            source['bot'].send_message(
                source['administrator_page'],
                "You can't use that command in administrator pages.",
                reply_to_message_id=source['message']['message_id'])
    else:
        source['bot'].send_message(
            source['administrator_page'],
            "Invalid command.",
            reply_to_message_id=source['message']['message_id'])


@sourced
def handle_message_from_superadmin(source):
    """ Will handle message from superadmin 
    that are not in the administrator page """
    if source['command'] in available_commands and not available_commands[
        source['command']][2]:
        available_commands[source['command']][0](source['bot'],
                                                 source['message'])


@sourced
def handle_message_from_private_chat(source):
    """ Will handle message from private chat """
    source['bot'].send_message(
        source['message']['chat']['id'],
        "If you want to use this bot in your groups too, then connect with @KoStard.",
        reply_to_message_id=source['message']['message_id'])


@sourced
def handle_message_from_unregistered_group(source):
    """ Will handle messages from groups """
    if source['command']:
        source['bot'].send_message(
            source['message']['chat']['id'],
            "If you want to use this bot in your groups too, then connect with @KoStard.",
            reply_to_message_id=source['message']['message_id'])
    else:
        pass  # When getting simple messages


@sourced
def handle_message_from_bot(source):
    """ Will handle message from bots """
    pass


@sourced
def handle_message_from_user(source):
    """ Handling message from user 
    [Saving]
    - text
    - command
    - participant_group
    - is_superadmin
    - is_administrator_page
    - administrator_page
    """
    save_to_data_stack(raw_text=source['message'].get("text"))
    save_to_data_stack(
        command=source['raw_text'][1:].split(" ")[0].
            split('@')[0] if source['raw_text'] and source['raw_text'][
            0] == '/' else '')  # This won't work with multiargumental commands
    save_to_data_stack(
        text=source['raw_text'] if not source['command'] else None)

    # Checking if the group is registered
    save_to_data_stack(
        participant_group=get_from_Model(
            ParticipantGroup, telegram_id=source["message"]["chat"]["id"]))
    # Checking if is a superadmin
    is_superadmin = not not SuperAdmin.objects.filter(user__id=source['message']['from']['id'])
    save_to_data_stack(is_superadmin=is_superadmin)
    # Checking if in an administrator page
    administrator_page = get_from_Model(
        AdministratorPage, telegram_id=source['message']['chat']['id'])
    save_to_data_stack(is_administrator_page=not not administrator_page)
    save_to_data_stack(administrator_page=administrator_page)

    if source['participant_group']:
        # If the participant group is already registered
        handle_message_from_participant_group()
    elif administrator_page:
        # If the message is in the administrator page
        handle_message_from_administrator_page()
    elif is_superadmin:
        # If the user if superadmin but is sending a message not in a registered group
        handle_message_from_superadmin()
    elif source['message']['chat']['type'] == 'private':
        # Will handle message from private chats
        handle_message_from_private_chat()
    elif source['message']['chat']['type'] in ('group', 'supergroup'):
        # Will handle message from groups
        handle_message_from_unregistered_group()
    else:
        print("Don't know what to do... :/")


def handle_message(bot, message):
    """ Handling Message """
    save_to_data_stack(message=message)
    if message['from']['is_bot']:
        handle_message_from_bot()
    else:
        handle_message_from_user()


def update_bot(bot: Bot, *, timeout=60):
    """ Will get bot updates """
    updates = get_updates(bot, timeout=timeout)
    for update in updates:
        message = update.get("message")
        handle_update(bot, update)
        bot.offset = update["update_id"] + 1
        bot.save()


def send_problem(bot: Bot, participant_group: ParticipantGroup, text, message):
    """ Will send problem -> default will be the next problem if available"""
    if participant_group.activeProblem:
        bot.send_message(
            participant_group,
            "You have to close active problem before sending another one.",
            reply_to_message_id=message['message_id'])
        return
    if len(text.split()) > 1:
        index = int(text.split()[1])
        try:
            problem: Problem = participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                index=index)
        except Problem.DoesNotExist:
            bot.send_message(
                participant_group,
                'Invalid problem number "{}".'.format(index),
                reply_to_message_id=message["message_id"],
            )
            return
        except AttributeError:  # If there is no activeSubjectGroupBinding
            bot.send_message(
                participant_group,
                'There is no active subject for this group.',
                reply_to_message_id=message["message_id"],
            )
            return
    else:
        problem: Problem = participant_group.activeSubjectGroupBinding.last_problem.next
        if not problem:
            bot.send_message(
                participant_group,
                'The subject is finished, no problem to send.',
                reply_to_message_id=message["message_id"],
            )
            return
    form_resp = bot.send_message(participant_group, str(problem))
    logging.debug("Sending problem {}".format(problem.index))
    logging.debug(form_resp)
    for problemimage in problem.problemimage_set.filter(for_answer=False):
        image = problemimage.image
        try:
            bot.send_image(
                participant_group,
                open(image.path, "rb"),
                reply_to_message_id=form_resp[0].get(
                    "message_id"),  # Temporarily disabling
                caption="Image of problem N{}.".format(problem.index),
            )
            logging.debug("Sending image for problem {}".format(problem.index))
            adm_log(
                bot, participant_group, "Sent image {} for problem N{}".format(
                    image, problem.index))
        except Exception as e:
            print("Can't send image {}".format(image))
            print(e)
            logging.info(e)
            adm_log(
                bot, participant_group,
                "Can't send image {} for problem N{}".format(
                    image, problem.index))
    participant_group.activeProblem = problem
    participant_group.save()
    participant_group.activeSubjectGroupBinding.last_problem = problem
    participant_group.activeSubjectGroupBinding.save()


def answer_problem(bot, participant_group, text, message):
    """ Will send the answer of the problem -> automatically is answering to the active problem """
    if not participant_group.activeProblem and len(text.split()) <= 1:
        bot.send_message(
            participant_group,
            "There is no active problem for this participant_group.",
            reply_to_message_id=message["message_id"],
        )
        return
    problem = participant_group.activeProblem
    if len(text.split()) > 1:
        index = int(text.split()[1])
        if problem and index > problem.index:
            bot.send_message(
                participant_group,
                "You can't send new problem's answer without opening it.",
                reply_to_message_id=message["message_id"],
            )
            return
        elif not problem or index < problem.index:
            try:
                problem = participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                    index=index)
            except Problem.DoesNotExist:
                bot.send_message(participant_group,
                                 "Invalid problem number {}.")
            else:
                bot.send_message(participant_group, problem.get_answer())
                for problemimage in problem.problemimage_set.filter(for_answer=True):
                    image = problemimage.image
                    try:
                        bot.send_image(
                            participant_group,
                            open(image.path, "rb"),
                            caption="Image of problem N{}'s answer.".format(problem.index),
                        )
                        logging.debug("Sending image for problem {}'s answer".format(problem.index))
                        print("Sending image for problem {}'s answer".format(problem.index))
                        adm_log(
                            bot, participant_group, "Sent image {} for problem N{}'s answer".format(
                                image, problem.index))
                    except Exception as e:
                        print("Can't send image {}".format(image))
                        print(e)
                        logging.info(e)
                        adm_log(
                            bot, participant_group,
                            "Can't send image {} for problem N{}'s answer.".format(
                                image, problem.index))
            return
    bot.send_message(participant_group, problem.get_answer())
    for problemimage in problem.problemimage_set.filter(for_answer=True):
        image = problemimage.image
        try:
            bot.send_image(
                participant_group,
                open(image.path, "rb"),
                caption="Image of problem N{}'s answer.".format(problem.index),
            )
            logging.debug("Sending image for problem {}'s answer".format(problem.index))
            print("Sending image for problem {}'s answer".format(problem.index))
            adm_log(
                bot, participant_group, "Sent image {} for problem N{}'s answer".format(
                    image, problem.index))
        except Exception as e:
            print("Can't send image {}".format(image))
            print(e)
            logging.info(e)
            adm_log(
                bot, participant_group,
                "Can't send image {} for problem N{}'s answer.".format(
                    image, problem.index))
    bot.send_message(participant_group, problem.close(participant_group))
    t_pages = participant_group.telegraphpage_set.all()
    if t_pages:  # Create the page manually with DynamicTelegraphPageCreator
        t_page = t_pages[
            len(t_pages) -
            1]  # Using last added page -> negative indexing is not supported
        t_account = t_page.account
        page_controller = DynamicTelegraphPageCreator(t_account.access_token)
        page_controller.load_and_set_page(t_page.path, return_content=False)
        page_controller.update_page(
            content=createGroupLeaderBoardForTelegraph(participant_group))
    participant_group.activeProblem = None
    participant_group.save()


def cancel_problem(bot: Bot, participant_group: ParticipantGroup, text: str,
                   message: dict):
    """ Will cancel the problem and remove all answers from the DB.  """
    if participant_group.activeProblem:
        answers = [
            answer for answer in Answer.objects.filter(
                group_specific_participant_data__participant_group=
                participant_group,
                problem=participant_group.activeProblem)
        ]
        for answer in answers:
            answer.delete()
        participant_group.activeSubjectGroupBinding.last_problem = participant_group.activeProblem.previous
        participant_group.activeSubjectGroupBinding.save()
        temp_problem = participant_group.activeProblem
        participant_group.activeProblem = None
        participant_group.save()
        bot.send_message(
            participant_group,
            "The problem {} is cancelled.".format(temp_problem.index),
            reply_to_message_id=message['message_id'])
    else:
        bot.send_message(
            participant_group,
            "There is not active problem to cancel.",
            reply_to_message_id=message['message_id'])


def start_in_participant_group(bot, participant_group, text,
                               message):  # Won't work in new groups
    """ Will create bot bindings with a given group """
    binding = BotBinding(bot=bot, participant_group=participant_group)
    binding.save()
    bot.send_message(
        participant_group,
        "This participant_group is now bound with me, to break the connection, use /stop command.",
        reply_to_message_id=message["message_id"],
    )


def remove_from_participant_group(bot, participant_group, text, message):
    """ Will remove bot binding with a given group """
    bot.botbinding_set.objects.get(bot=bot).delete()
    bot.send_message(
        participant_group,
        "The connection was successfully stopped.",
        reply_to_message_id=message["message_id"],
    )


def add_subject(bot, participant_group, text, message):
    """ Will add subject to the group and select it if the group doesn't have active subject """
    pass


def select_subject(bot: Bot, participant_group: ParticipantGroup, text: str,
                   message: dict):
    """ Will select subject in the group 
    Give with message
     - index
    """
    ''.isnumeric
    if not ' ' in text or not text.split(' ')[1].isnumeric():
        bot.send_message(
            participant_group,
            """You have to give the index of subject to select.
You can get indexes with /subjects_list command.""",
            reply_to_message_id=message['message_id'])
        return
    index = int(text.split(' ')[1])
    subject_group_bindings = participant_group.subjectgroupbinding_set.all()
    if index not in range(1, len(subject_group_bindings) + 1):
        bot.send_message(
            participant_group,
            """You have to give valid subject index.
You can get indexes with /subjects_list command.""",
            reply_to_message_id=message['message_id'])
        return
    participant_group.activeSubjectGroupBinding = subject_group_bindings[index
                                                                         - 1]
    participant_group.activeProblem = None
    participant_group.save()
    bot.send_message(
        participant_group,
        """Subject "{}" is now selected.""".format(
            subject_group_bindings[index - 1].subject.name),
        reply_to_message_id=message['message_id'])


def active_subject(bot: Bot, participant_group: ParticipantGroup, text: str,
                   message: dict):
    """ Will send active subject to the group if available """
    if participant_group.activeSubjectGroupBinding:
        bot.send_message(
            participant_group,
            """Subject "{}" is active.""".format(
                participant_group.activeSubjectGroupBinding.subject.name),
            reply_to_message_id=message['message_id'])
    else:
        bot.send_message(
            participant_group,
            """There is no active subject in this group.""",
            reply_to_message_id=message['message_id'])


def finish_subject(bot, participant_group, text, message):
    """ Will close subject in the group """
    pass


def get_subjects_list(bot: Bot, participant_group: ParticipantGroup, text,
                      message):
    """ Will send subjects list for current group """
    bot.send_message(
        participant_group,
        """This is the subjects list for current group:
{}""".format('\n'.join(
            ' - '.join(str(e) for e in el)
            for el in enumerate((binding.subject.name
                                 for binding in participant_group.
                                subjectgroupbinding_set.all()), 1))),
        reply_to_message_id=message['message_id'])


def get_score(bot, participant_group, text, message):
    """ Will send the score of the participant to the group """
    participant = Participant.objects.filter(pk=message["from"]["id"])
    if participant:
        participant = participant[0]
        specific = GroupSpecificParticipantData.objects.filter(
            participant=participant, participant_group=participant_group)
        if specific:
            specific = specific[0]
            bot.send_message(
                participant_group,
                "{}'s score is {}".format(str(participant), specific.score),
                reply_to_message_id=message["message_id"],
            )


def report(bot, participant_group, text, message):
    """ Temp -> Will be created """
    pass


USER_DEFINED_PROBLEM_TEMPLATE = r"""Name-.+
Definition-.+
Variant a-.+
Variant b-.+
Variant c-.+
Variant d-.+
Variant e-.+
Right variant-[abcdeABCDE]"""

USER_DEFINED_PROBLEM_TEMPLATE_READABLE = r"""Name-[WRITE HERE YOUR TEXT]
Definition-[WRITE HERE YOUR TEXT]
Variant a-[WRITE HERE YOUR TEXT]
Variant b-[WRITE HERE YOUR TEXT]
Variant c-[WRITE HERE YOUR TEXT]
Variant d-[WRITE HERE YOUR TEXT]
Variant e-[WRITE HERE YOUR TEXT]
Right variant-[abcdeABCDE]"""


def add_user_defined_problem(bot: Bot, participant_group: ParticipantGroup,
                             text: str, message: dict):
    """ Add User-defined Problem """
    pass


def start_in_administrator_page(bot: Bot, message):
    """ Will save administrator page """
    administrator_page = AdministratorPage(
        telegram_id=message["chat"]["id"],
        username=message["chat"].get("username"),
        title=message["chat"].get("title"),
        type=(GroupType.objects.filter(name=message["chat"].get("type"))
              or [None])[0],
    )
    administrator_page.save()
    bot.send_message(
        administrator_page,
        "Congratulations, this group is now registered as an administrator page.",
        reply_to_message_id=message['message_id'])


def stop_in_administrator_page(bot: Bot, administrator_page: AdministratorPage,
                               text, message):
    """ Will remove administrator page """
    chat_id = administrator_page.telegram_id
    administrator_page.delete()
    bot.send_message(
        chat_id,
        'This target is no longer an administrator page, so you won\'t get any log here anymore.',
        reply_to_message_id=message['message_id'])


def status_in_administrator_page(bot: Bot,
                                 administrator_page: AdministratorPage,
                                 text: str, message: dict) -> None:
    """ Will log the status to the administrator page """
    try:
        answers = administrator_page.participant_group.activeProblem.answer_set.filter(
            processed=False,
            group_specific_participant_data__participant_group=
            administrator_page.participant_group)
    except AttributeError:  # If there is no active problem
        bot.send_message(
            administrator_page,
            """There is no active problem.""",
            reply_to_message_id=message['message_id'])
        return
    answers_count = (el for el in ((
        variant,
        len([answer for answer in answers
             if answer.answer.upper() == variant]))
        for variant in 'ABCDE') if el[1])
    bot.send_message(
        administrator_page,
        """Current status for problem {} is{}
For more contact with @KoStard""".format(
            administrator_page.participant_group.activeProblem.index,
            ''.join('\n{} - {}'.format(*el) for el in answers_count)
            if answers_count else ' - No one answered.'),
        reply_to_message_id=message['message_id'])


def root_test(bot: Bot, administrator_page: AdministratorPage, text: str,
              message: dict) -> None:
    """ This is used for some root testings of the bot """
    ### Now will be used for image sending test
    try:
        bot.send_image(
            administrator_page,
            open('../media/images/Photos/image005.png', 'rb'),
            reply_to_message_id=message['message_id']
        )  # Is working, so the bug with image sending is solved.
    except Exception as e:
        print(e)
        unilog("Can't send image in root_test")


def register_participant_group(bot: Bot, message: dict):
    """ Will register chat as a participant group """
    chat = message.get("chat")
    tp = get_from_Model(GroupType, name=chat['type'])
    if not chat:
        logging.info("Can't get chat to register.")
        pass
    participant_group = get_from_Model(
        ParticipantGroup, telegram_id=chat['id'])
    if participant_group:
        bot.send_message(
            participant_group,
            "This group is already registered.",
            reply_to_message_id=message['message_id']
        )  # Maybe add reference to the documentation with this message
    elif not tp:
        bot.send_message(
            chat['id'],
            "Unknown type of group, to improve this connect with @KoStard.",
            reply_to_message_id=message['message_id'])
    else:
        participant_group = ParticipantGroup(
            telegram_id=chat['id'],
            username=chat.get('username'),
            title=chat.get('title'),
            type=tp)
        participant_group.save()
        binding = BotBinding(bot=bot, participant_group=participant_group)
        binding.save()
        bot.send_message(
            participant_group,
            """This group is now registered and a binding is created,\
so now the bot will listen to your commands.""",
            reply_to_message_id=message['message_id'])


@sourced
def handle_restart_command(source):
    """
    Will restart the script
    - Maybe will result to problems when in multi-bot mode, because will restart the program, while other
        bot's commands are being processed
    """
    unilog("Restarting")
    update_and_restart()


# - (function, min_priority_level, needs_binding)
available_commands = {
    "send": (send_problem, 6, True),
    "answer": (answer_problem, 6, True),
    "cancel_problem": (cancel_problem, 6, True),
    "start_participant": (start_in_participant_group, 8, False),
    "stop_participant": (remove_from_participant_group, 8, True),
    "add_subject": (add_subject, 9, True),
    "select_subject": (select_subject, 9, True),
    "active_subject": (active_subject, 8, True),
    "finish_subject": (finish_subject, 9, True),
    "subjects_list": (get_subjects_list, 9, True),
    # "score": (get_score, 0, True), # Stopping this, because participants can see their scores in the leaderboard
    "report": (report, 2, True),
    "add_special_problem": (add_user_defined_problem, 4, True),
    "start_admin": (start_in_administrator_page, 'superadmin', False),
    "stop_admin": (stop_in_administrator_page, 'superadmin', True),
    "status": (status_in_administrator_page, 8, True),
    "root_test": (root_test, 'superadmin', True),
    "register": (register_participant_group, 'superadmin', False),
    "restart": (handle_restart_command, 'superadmin', True),
}


def createGroupLeaderBoard(participant_group: ParticipantGroup):
    """ Will process and present the data for group leaderboards """
    gss = [{
        "participant":
            gs.participant,
        "score":
            gs.score,
        "percentage":
            gs.percentage,
        "standard_role":
            safe_getter(gs.highest_standard_role_binding, "role"),
        "non_standard_role":
            safe_getter(gs.highest_non_standard_role_binding, "role"),
    } for gs in sorted(
        (gs for gs in participant_group.groupspecificparticipantdata_set.all()
         if gs.score),
        key=lambda gs: [gs.score, gs.percentage],
    )[::-1]]
    return gss


def get_promoted_participants_list_for_leaderboard(
        participant_group: ParticipantGroup):
    """ Will process data of promoted participants for group leaderboards """
    admin_gss = [{
        "participant":
            gs.participant,
        "non_standard_role":
            gs.highest_non_standard_role_binding.role,
    } for gs in sorted(
        (gs for gs in participant_group.groupspecificparticipantdata_set.all()
         if gs.highest_non_standard_role_binding),
        key=
        lambda gs: [gs.highest_non_standard_role_binding.role.priority_level],
    )[::-1]]
    return admin_gss


def createGroupLeaderBoardForTelegraph(participant_group: ParticipantGroup,
                                       *,
                                       max_limit=0):
    """ Will create content for leaderboard telegraph page """
    raw_leaderboard = createGroupLeaderBoard(participant_group)
    raw_promoted_list = get_promoted_participants_list_for_leaderboard(
        participant_group)
    res = []

    res.append(
        DynamicTelegraphPageCreator.create_blockquote([
            "Here you see dynamically updating Leaderboard of ",
            DynamicTelegraphPageCreator.create_link(
                "Pathology Group [MedStard]",
                'https://t.me/Pathology_Group'), '.\n', "This is a part of ",
            DynamicTelegraphPageCreator.create_link("MedStard",
                                                    "https://t.me/MedStard"),
            ", where you can find much more stuff related to medicine, so welcome to our community."
        ]))

    last_role = None
    roles_number = 0
    current_list = None
    for gs in (raw_leaderboard[:max_limit] if max_limit else raw_leaderboard):
        if gs['standard_role'] != last_role:
            if last_role:
                res.append(DynamicTelegraphPageCreator.hr)
            roles_number += 1
            res.append(
                DynamicTelegraphPageCreator.create_title(
                    4, '{}. {} {}'.format(
                        roles_number, gs['standard_role'].name,
                        '⭐' * gs['standard_role'].priority_level)))
            ordered_list = DynamicTelegraphPageCreator.create_ordered_list()
            res.append(ordered_list)
            current_list = ordered_list['children']
            last_role = gs['standard_role']
        if roles_number == 1:
            current_list.append(
                DynamicTelegraphPageCreator.create_list_item(
                    DynamicTelegraphPageCreator.create_bold([
                        DynamicTelegraphPageCreator.create_code([
                            DynamicTelegraphPageCreator.create_bold(
                                '{}'.format(gs['score'])), 'xp{}'.format(
                                (' [{}%]'.format(gs['percentage'])
                                 if gs['percentage'] is not None else ''))
                        ]), ' - {}'.format(gs['participant'].full_name)
                    ])))
        else:
            current_list.append(
                DynamicTelegraphPageCreator.create_list_item([
                    DynamicTelegraphPageCreator.create_code([
                        DynamicTelegraphPageCreator.create_bold('{}'.format(
                            gs['score'])), 'xp{}'.format(
                            (' [{}%]'.format(gs['percentage'])
                             if gs['percentage'] is not None else ''))
                    ]), ' - {}'.format(gs['participant'].full_name)
                ]))
    res.append(DynamicTelegraphPageCreator.hr)
    res.append(
        DynamicTelegraphPageCreator.create_title(3, '{}'.format("Team")))
    ordered_list = DynamicTelegraphPageCreator.create_ordered_list()
    res.append(ordered_list)
    current_list = ordered_list['children']
    for gs in raw_promoted_list:
        current_list.append(
            DynamicTelegraphPageCreator.create_list_item(
                DynamicTelegraphPageCreator.create_bold([
                    gs['non_standard_role'].name + ' - ',
                    DynamicTelegraphPageCreator.create_link(
                        gs['participant'].full_name,
                        'https://telegram.me/{}'.format(
                            gs['participant'].username)) if
                    gs['participant'].username else gs['participant'].full_name
                ])))
    return res


def create_and_save_telegraph_page(t_account: TelegraphAccount,
                                   title: str,
                                   content: list,
                                   participant_group: ParticipantGroup = None):
    """ This function will be used to create new pages for new groups - not used for now  """
    d = DynamicTelegraphPageCreator(t_account.access_token)
    p = d.create_page(title, content, return_content=True)
    d.load_and_set_page(p['path'])
    TelegraphPage(
        path=p['path'],
        url=p['url'],
        account=t_account,
        participant_group=participant_group).save()
    return d
