from main.models import *
from main.universals import get_response, configure_logging, safe_getter, get_from_Model, update_and_restart
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator
from django.utils import timezone
from time import sleep
from datetime import datetime
import logging
from .source_manager import SourceManager

"""
Will contain some function relations and arguments to run them after a command is processed
{bot_object_id: [{func: f, args: [], kwargs: {}}]}
"""
POST_PROCESSING_STACK = {}


def add_to_post_processing_stack(bot: Bot, func, *args, **kwargs):
    """
    :param bot: current bot object
    :param func: has to be either function or dict with func key that relates to a function
    :param args: has to be used when the func is function
    :param kwargs: has to be used when the func is function
    :return:
    """
    if bot.id not in POST_PROCESSING_STACK:
        POST_PROCESSING_STACK[bot.id] = []
    if isinstance(func, dict):
        POST_PROCESSING_STACK[bot.id].append(func)
    else:
        POST_PROCESSING_STACK[bot.id].append({
            'func': func,
            'args': args,
            'kwargs': kwargs
        })


# configure_logging()


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


class Worker:
    def __init__(self, bot: Bot):
        self.source = SourceManager(bot.id)  # Don't adding layer yet
        self.bot = bot

        # - (function, min_priority_level, needs_binding)
        self.available_commands = {
            "send": (self.send_problem, 6, True),
            "answer": (self.answer_problem, 6, True),
            "cancel_problem": (self.cancel_problem, 6, True),
            "start_participant": (self.start_in_participant_group, 8, False),
            "stop_participant": (self.remove_from_participant_group, 8, True),
            "add_subject": (self.add_subject, 9, True),
            "select_subject": (self.select_subject, 9, True),
            "active_subject": (self.active_subject, 8, True),
            "finish_subject": (self.finish_subject, 9, True),
            "subjects_list": (self.get_subjects_list, 9, True),
            # "score": (self.get_score, 0, True), # Stopping this, because participants can see their scores in the leaderboard
            "report": (self.report, 2, True),
            "add_special_problem": (self.add_user_defined_problem, 4, True),
            "start_admin": (self.start_in_administrator_page, 'superadmin', False),
            "stop_admin": (self.stop_in_administrator_page, 'superadmin', True),
            "status": (self.status_in_administrator_page, 8, True),
            "root_test": (self.root_test, 'superadmin', True),
            "register": (self.register_participant_group, 'superadmin', False),
            "restart": (self.handle_restart_command, 'superadmin', True),
        }

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __getattr__(self, item):
        if item == 'source' or item in self.__dict__:
            return self.__dict__[item]
        return self.__dict__['source'][item]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __setattr__(self, key, value):
        if key == 'source' or key in self.__dict__ or self.source.is_empty:
            self.__dict__[key] = value
        else:
            self.__dict__['source'][key] = value

    def get_updates(self, *, update_last_updated=True, timeout=60):
        """ Will return bot updates """
        url = self.bot.base_url + "getUpdates"  # The URL of getting bot updates
        updates = get_response(
            url,
            payload={
                'offset': self.bot.offset or "",  # Setting offset
                'timeout':
                    timeout  # Setting timeout to delay empty updates handling
            })
        if update_last_updated:
            self.bot.last_updated = timezone.now()
            self.bot.save()
        return updates

    def adm_log(self, message):
        """ Will log to the administrator page if available """
        if not self.is_administrator_page:
            self.bot.send_message(self.participant_group.administratorpage, message)
        elif isinstance(self.participant_group, AdministratorPage):
            self.bot.send_message(self.participant_group, message)

    def check_entities(self):
        """ Will check message for entities and check participant's permissions to use them """
        resp = {"status": True, "unknown": False}
        priority_level = self[
            'groupspecificparticipantdata'].highest_role.priority_level
        for entity in self['entities']:
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

    def check_message_bindings(self):
        """ Will check message for bindings and check participant's permissions to use them """
        resp = {"status": True, "unknown": False}
        priority_level = self[
            'groupspecificparticipantdata'].highest_role.priority_level
        for message_binding in AVAILABLE_MESSAGE_BINDINGS:
            if message_binding in self['message'] and AVAILABLE_MESSAGE_BINDINGS[
                message_binding] > priority_level:
                if resp["status"]: resp["status"] = False
                if "cause" not in resp:
                    resp["cause"] = []
                resp["cause"].append(
                    "\"{}\" message binding is not allowed for users with priority level lower than {}"
                        .format(message_binding,
                                AVAILABLE_MESSAGE_BINDINGS[message_binding]))
        return resp

    def run_post_processing_functions(self):
        # Can't be sourced, because this has to be called after the bot's offset is changed
        if self.bot.id not in POST_PROCESSING_STACK:
            return
        funcs = POST_PROCESSING_STACK[self.bot.id]
        del POST_PROCESSING_STACK[self.bot.id]
        for func_data in funcs:
            func_data['func'](*(func_data.get('args') or []), **(func_data.get('kwargs') or {}))

    def handle_update(self, update, *, catch_exceptions=False) -> bool:
        """ Handling Update
        - True -> the process is finished normal
        - False -> catched exception
        - exception -> when exception was raised, but catch_exception is False

        Adding {update, message, bot} to the DATA_STACK
        """
        message = update.get('message')
        self.source.append(
            update=update,
            message=message,
            bot=self.bot
        )  # Adding the dictionary for this update
        catched_exception = False
        if message:
            try:
                self.handle_message(message)
            except Exception as exception:
                if catch_exceptions:
                    catched_exception = True
                    return False
                else:
                    self.source.pop()
                    raise
        self.source.pop()
        return True

    def create_log_from_message(self) -> str:
        """ Creating log from Telegram message """
        pr_m = ''  # Priority marker
        if self['groupspecificparticipantdata'].is_admin:
            pr_m = '🛡️'
        else:
            pr_m = '⭐' * max(self['groupspecificparticipantdata'].highest_standard_role_binding.role.priority_level, 0)

        if pr_m:
            pr_m += ' '

        name = self['participant'].name
        data = (
                       (self['raw_text'] or '') +
                       ('' if not self['entities'] else
                        '\nFound entities: ' + ', '.join(entity['type']
                                                         for entity in self['entities']))
               ) or ', '.join(
            message_binding for message_binding in AVAILABLE_MESSAGE_BINDINGS
            if message_binding in self['message']
        ) or (("New chat member" if len(self['message']['new_chat_members']) == 1
                                    and self['message']['new_chat_members'][0]['id'] ==
                                    self['message']['from']['id'] else 'Invited {}'.format(', '.join(
            user['first_name'] or user['last_name'] or user['username']
            for user in self['message'].get('new_chat_members'))))
              if 'new_chat_members' in self['message'] else '')
        result = f"{pr_m}{name} -> {data}"
        return result

    def unilog(self, log: str) -> None:
        """ Will log to the:
        - stdout
        - logging
        - adm_page
        """
        print(log)  # Logging to stdout
        logging.info(f'{timezone.now()} | {log}')  # Logging to logs file
        self.adm_log(log)  # Logging to administrator page

    def get_or_register_message_sender_participant(self) -> Participant:
        """
        Will get if registered or register message sender as a participant
        """
        if self.source.get('message'):
            participant = get_from_Model(
                Participant, id=self['message']['from']['id'])
            if not participant:
                participant = register_participant(self['message']['from'])
            self.source.participant = participant
            return participant
        else:
            self.source.participant = None
            raise ValueError("INVALID MESSAGE DATA")

    def get_or_register_groupspecificparticipantdata_of_active_participant(
            self) -> GroupSpecificParticipantData:
        """
        Will get if registered or register participant in active participant_group
        """
        if self['participant_group'] and self['participant']:
            gspd = get_from_Model(
                self['participant'].groupspecificparticipantdata_set,
                participant_group=self['participant_group'], _mode='direct')
            if not gspd:
                gspd = register_groupspecificparticipantdata(
                    participant=self['participant'],
                    participant_group=self['participant_group'])
            self.source.groupspecificparticipantdata = gspd
            return gspd
        else:
            self.source.groupspecificparticipantdata = None
            raise ValueError(
                "INVALID DATA IN get_or_register_groupspecificparticipantdata_of_active_participant"
            )

    def register_participant_group_new_members(self) -> list:
        """
        Will register all participant group new members
        """
        new_members = []
        for new_member_data in safe_getter(
                self.source, 'message.new_chat_members', default=[], mode='DICT'):
            participant = get_from_Model(Participant, id=new_member_data['id'])
            if not participant:
                participant = register_participant(new_member_data)
            gspd = get_from_Model(
                participant.groupspecificparticipantdata_set,
                participant_group=self['participant_group'], _mode='direct')
            if not gspd:
                gspd = register_groupspecificparticipantdata(
                    participant=participant,
                    participant_group=self['participant_group'],
                    joined=datetime.fromtimestamp(
                        self['message']["date"], tz=timezone.get_current_timezone()),
                )
            new_members.append((participant, gspd))
        self.source.new_members_models = new_members
        return new_members

    def handle_entities(self) -> bool:
        """ Will handle entities from self's message """
        entities = safe_getter(self.source, 'message.entities', mode='dict', default=[])
        self.entities = entities
        entities_check_response = self.check_entities()
        self.entities_check_response = entities_check_response
        logging.info("Found Entity: " + str(entities_check_response))
        if not entities_check_response["status"]:
            if not entities_check_response["unknown"]:
                # Sending answer message to the message with restricted entities
                self['bot'].send_message(
                    self['participant_group'],
                    "Dear {}, your message will be removed, because {}.\nYou have [{}] roles.\
                    \nFor more information contact with @KoStard".format(
                        self['participant'].name,
                        entities_check_response["cause"],
                        ", ".join("{} - {}".format(
                            participantgroupbinding.role.name,
                            participantgroupbinding.role.priority_level,
                        ) for participantgroupbinding in
                                  self['groupspecificparticipantdata'].
                                  participantgroupbinding_set.all())
                        or '-',
                    ),
                    reply_to_message_id=self['message']["message_id"],
                )
                # Removing message with restricted entities
                self['bot'].delete_message(self['participant_group'],
                                           self['message']["message_id"])
                # Creating violation
                self['groupspecificparticipantdata'].create_violation(
                    get_from_Model(
                        ViolationType,
                        value='message_entity_low_permissions'),
                    datetime.fromtimestamp(
                        self['message']["date"],
                        tz=timezone.get_current_timezone()))
                return False
        return True

    def handle_message_bindings(self) -> bool:
        message_bindings_check_response = self.check_message_bindings()
        if not message_bindings_check_response["status"]:
            logging.info(message_bindings_check_response["cause"])
            if not message_bindings_check_response["unknown"]:
                self['bot'].send_message(
                    self['participant_group'],
                    "Dear {}, your message will be removed, because {}.\nYou have [{}] roles.\
                    \nFor more information contact with @KoStard".format(
                        self['participant'].name,
                        ', '.join(message_bindings_check_response["cause"]),
                        ", ".join("{} - {}".format(
                            participantgroupbinding.role.name,
                            participantgroupbinding.role.priority_level,
                        ) for participantgroupbinding in
                                  self['groupspecificparticipantdata'].
                                  participantgroupbinding_set.all()),
                    ),
                    reply_to_message_id=self['message']["message_id"],
                )
                self['bot'].delete_message(self['participant_group'],
                                           self['message']["message_id"])
                self['groupspecificparticipantdata'].create_violation(
                    get_from_Model(
                        ViolationType,
                        value='message_binding_low_permissions'))
                return False
        return True

    def handle_answer_change(self):
        """
        Catching when participant is trying to change the answer
        """
        if not self.get('bot') or not self.get('message'):
            return
        if self['old_answer'].answer.upper() == self['variant'].upper():
            # Sending same answer again
            self.unilog("{} is trying to answer {} again".format(
                self['participant'], self['variant']))
            self['bot'].delete_message(self['participant_group'],
                                       self['message']['message_id'])
        else:
            self.unilog("{} is trying to change answer {} to {}".format(
                self['participant'], self['old_answer'].answer,
                self['variant']))
            self['bot'].send_message(
                self['participant_group'],
                'Dear {}, you can\'t change your answer.'.format(
                    self['participant'].name),
                reply_to_message_id=self['message']['message_id'])

    def accept_answer(self) -> Answer:
        """
        Accepting answer - right or wrong
        """
        if self['variant'] == self['participant_group'].activeProblem.right_variant.upper():
            print("Right answer from {} N{}".format(
                self['participant'],
                len(
                    self['participant_group'].activeProblem.answer_set.filter(
                        right=True,
                        processed=False,
                        group_specific_participant_data__participant_group=
                        self['participant_group'])) + 1))
        else:
            print("Wrong answer from {} - Right answers {}".format(
                self['participant'],
                len(
                    self['participant_group'].activeProblem.answer_set.filter(
                        right=True,
                        processed=False,
                        group_specific_participant_data__participant_group=self[
                            'participant_group']))))
        answer = Answer(
            problem=self['participant_group'].activeProblem,
            answer=self['variant'],
            right=self['variant'] == self['participant_group'].activeProblem.right_variant.upper(),
            processed=False,
            group_specific_participant_data=self['groupspecificparticipantdata'],
            date=timezone.now(),
        )
        answer.save()
        return answer

    def handle_answers_from_testing_bots(self):
        """
        Will handle answers from testing bots
        """
        self.unilog("Answer from testing bot's controlling groups")

    def handle_answer(self):
        """
        Will handle participant answers
        """
        if not self['participant_group'].activeProblem:
            print(f"There is no active problem in {self['participant_group']}")
            return False
        old_answer = get_from_Model(
            self['participant_group'].activeProblem.answer_set,
            group_specific_participant_data=self[
                'groupspecificparticipantdata'],
            processed=False,
            _mode='direct')
        self.source.old_answer = old_answer
        if old_answer:
            self.handle_answer_change()
        elif self['bot'].for_testing:
            self.handle_answers_from_testing_bots()
        else:
            self.accept_answer()

    def handle_pgm_text(self):
        """
        Will handle text from participant_group message
        """
        if not self['text']:
            return  # There is no text in the message
        if len(self['text']) == 1 and self['text'].upper() in ('A', 'B', 'C', 'D', 'E'):
            self.source.variant = self['text'].upper()
            self.handle_answer()
        else:
            pass  # Just regular message in participant group

    def handle_superadmin_commands_in_pg(self):
        self.available_commands[
            self['command']][0]()

    def accept_command_in_pg(self):
        self.available_commands[self['command']][0]()

    def reject_command_in_pg(self):
        self['bot'].send_message(
            self['participant_group'],
            ('Sorry dear {}, you don\'t have permission to use ' +
             'command "{}" - your highest role is "{}".').format(
                self['participant'], self['command'],
                self['groupspecificparticipantdata'].highest_role.name),
            reply_to_message_id=self['message']["message_id"],
        )
        self['groupspecificparticipantdata'].create_violation(
            get_from_Model(ViolationType, value='command_low_permissions'))

    def handle_pgm_commands(self):
        """
        Will handle commands from participant_group message
        """
        if not self['command']:
            return
        if self['command'] in self.available_commands:
            priority_level = self[
                'groupspecificparticipantdata'].highest_role.priority_level
            if (self.available_commands[self['command']][1] == 'superadmin'
                    and safe_getter(self['participant'], 'superadmin')
            ):
                self.handle_superadmin_commands_in_pg()
            elif (safe_getter(self['participant'], 'superadmin')
                  or priority_level >= self.available_commands[self['command']][1]
            ) and self['command'] != 'status':
                self.accept_command_in_pg()
            else:
                self.reject_command_in_pg()
        elif self['command']:
            self['bot'].send_message(
                self['participant_group'],
                'Invalid command "{}"'.format(self['command']),
                reply_to_message_id=self['message']["message_id"],
            )

    def handle_message_from_participant_group(self):
        """
        Will handle message from participant group
        """
        self.get_or_register_message_sender_participant()
        self.get_or_register_groupspecificparticipantdata_of_active_participant()
        self.register_participant_group_new_members()
        if self.handle_entities() and self.handle_message_bindings():
            self.unilog(self.create_log_from_message())
            self.handle_pgm_text()
            self.handle_pgm_commands()
        else:
            self.unilog(self.create_log_from_message())

    def handle_message_from_administrator_page(self):
        """ Will handle message from administrator page
        + superadmins """
        if not self['command']:
            return  # Just text
        if self['command'] in self.available_commands:
            if (
                    self.available_commands[self['command']][1] == 'superadmin'
                    or self['command'] == 'status'
            ) and self.available_commands[self['command']][2]:
                self.available_commands[self['command']][0]()
            else:
                self['bot'].send_message(
                    self['administrator_page'],
                    "You can't use that command in administrator pages.",
                    reply_to_message_id=self['message']['message_id'])
        else:
            self['bot'].send_message(
                self['administrator_page'],
                "Invalid command.",
                reply_to_message_id=self['message']['message_id'])

    def handle_message_from_superadmin(self):
        """ Will handle message from superadmin
        that are not in the administrator page """
        if self['command'] in self.available_commands and not self.available_commands[
            self['command']][2]:
            self.available_commands[self['command']][0]()

    def handle_message_from_private_chat(self):
        """ Will handle message from private chat """
        self['bot'].send_message(
            self['message']['chat']['id'],
            "If you want to use this bot in your groups too, then connect with @KoStard.",
            reply_to_message_id=self['message']['message_id'])

    def handle_message_from_unregistered_group(self):
        """ Will handle messages from groups """
        if self['command']:
            self['bot'].send_message(
                self['message']['chat']['id'],
                "If you want to use this bot in your groups too, then connect with @KoStard.",
                reply_to_message_id=self['message']['message_id'])
        else:
            pass  # When getting simple messages

    def handle_message_from_bot(self):
        """ Will handle message from bots """
        pass

    def handle_message_from_user(self):
        """ Handling message from user
        [Saving]
        - text
        - command
        - participant_group
        - is_superadmin
        - is_administrator_page
        - administrator_page
        """
        self.source.raw_text = self['message'].get("text")
        self.source.command = self['raw_text'][1:].split(" ")[0].split('@')[0] if self['raw_text'] and self['raw_text'][
            0] == '/' else ''  # This won't work with multiargumental commands
        self.source.text = self['raw_text'] if not self['command'] else None

        # Checking if the group is registered
        self.source.participant_group = get_from_Model(
            ParticipantGroup, telegram_id=self["message"]["chat"]["id"])
        # Checking if is a superadmin
        is_superadmin = not not SuperAdmin.objects.filter(user__id=self['message']['from']['id'])
        self.source.is_superadmin = is_superadmin
        # Checking if in an administrator page
        administrator_page = get_from_Model(
            AdministratorPage, telegram_id=self['message']['chat']['id'])
        self.source.is_administrator_page = not not administrator_page
        self.source.administrator_page = administrator_page

        if self['participant_group']:
            # If the participant group is already registered
            self.handle_message_from_participant_group()
        elif administrator_page:
            # If the message is in the administrator page
            self.handle_message_from_administrator_page()
        elif is_superadmin:
            # If the user if superadmin but is sending a message not in a registered group
            self.handle_message_from_superadmin()
        elif self['message']['chat']['type'] == 'private':
            # Will handle message from private chats
            self.handle_message_from_private_chat()
        elif self['message']['chat']['type'] in ('group', 'supergroup'):
            # Will handle message from groups
            self.handle_message_from_unregistered_group()
        else:
            print("Don't know what to do... :/")

    def handle_message(self, message):
        """ Handling Message """
        self.source.message = message
        if message['from']['is_bot']:
            self.handle_message_from_bot()
        else:
            self.handle_message_from_user()

    def update_bot(self, *, timeout=60):
        """ Will get bot updates """
        updates = self.get_updates(timeout=timeout)
        for update in updates:
            self.handle_update(update)
            self.bot.offset = update["update_id"] + 1
            self.bot.save()
            self.run_post_processing_functions()

    def send_problem(self):
        """ Will send problem -> default will be the next problem if available"""
        if self.source.participant_group.activeProblem:
            self.source.bot.send_message(
                self.source.participant_group,
                "You have to close active problem before sending another one.",
                reply_to_message_id=self.source.message['message_id'])
            return
        if len(self.source.raw_text.split()) > 1:
            index = int(self.source.raw_text.split()[1])
            try:
                problem: Problem = self.source.participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                    index=index)
            except Problem.DoesNotExist:
                self.source.bot.send_message(
                    self.source.participant_group,
                    'Invalid problem number "{}".'.format(index),
                    reply_to_message_id=self.source.message["message_id"],
                )
                return
            except AttributeError:  # If there is no activeSubjectGroupBinding
                self.source.bot.send_message(
                    self.source.participant_group,
                    'There is no active subject for this group.',
                    reply_to_message_id=self.source.message["message_id"],
                )
                return
        else:
            problem: Problem = self.source.participant_group.activeSubjectGroupBinding.last_problem.next
            if not problem:
                self.source.bot.send_message(
                    self.source.participant_group,
                    'The subject is finished, no problem to send.',
                    reply_to_message_id=self.source.message["message_id"],
                )
                return
        form_resp = self.source.bot.send_message(self.source.participant_group, str(problem))
        logging.debug("Sending problem {}".format(problem.index))
        logging.debug(form_resp)
        for problemimage in problem.problemimage_set.filter(for_answer=False):
            image = problemimage.image
            try:
                self.source.bot.send_image(
                    self.source.participant_group,
                    open(image.path, "rb"),
                    reply_to_message_id=form_resp[0].get(
                        "message_id"),  # Temporarily disabling
                    caption="Image of problem N{}.".format(problem.index),
                )
                logging.debug("Sending image for problem {}".format(problem.index))
                self.adm_log("Sent image {} for problem N{}".format(
                    image, problem.index))
            except Exception as e:
                print("Can't send image {}".format(image))
                print(e)
                logging.info(e)
                self.adm_log(
                    "Can't send image {} for problem N{}".format(
                        image, problem.index))
        self.source.participant_group.activeProblem = problem
        self.source.participant_group.save()
        self.source.participant_group.activeSubjectGroupBinding.last_problem = problem
        self.source.participant_group.activeSubjectGroupBinding.save()

    def answer_problem(self):
        """ Will send the answer of the problem -> automatically is answering to the active problem """
        if not self.source.participant_group.activeProblem and len(self.source.raw_text.split()) <= 1:
            self.source.bot.send_message(
                self.source.participant_group,
                "There is no active problem for this participant_group.",
                reply_to_message_id=self.source.message["message_id"],
            )
            return
        problem = self.source.participant_group.activeProblem
        if len(self.source.raw_text.split()) > 1:
            index = int(self.source.raw_text.split()[1])
            if problem and index > problem.index:
                self.source.bot.send_message(
                    self.source.participant_group,
                    "You can't send new problem's answer without opening it.",
                    reply_to_message_id=self.source.message["message_id"],
                )
                return
            elif not problem or index < problem.index:
                try:
                    problem = self.source.participant_group.activeSubjectGroupBinding.subject.problem_set.get(
                        index=index)
                except Problem.DoesNotExist:
                    self.source.bot.send_message(self.source.participant_group,
                                                 "Invalid problem number {}.")
                else:
                    self.source.bot.send_message(self.source.participant_group, problem.get_answer())
                    for problemimage in problem.problemimage_set.filter(for_answer=True):
                        image = problemimage.image
                        try:
                            self.source.bot.send_image(
                                self.source.participant_group,
                                open(image.path, "rb"),
                                caption="Image of problem N{}'s answer.".format(problem.index),
                            )
                            self.unilog("Sending image for problem {}'s answer".format(problem.index))
                        except Exception as e:
                            self.unilog("Can't send image {} for problem N{}'s answer.".format(
                                image, problem.index))
                            print(e)
                            logging.info(e)
                return
        self.source.bot.send_message(self.source.participant_group, problem.get_answer())
        for problemimage in problem.problemimage_set.filter(for_answer=True):
            image = problemimage.image
            try:
                self.source.bot.send_image(
                    self.source.participant_group,
                    open(image.path, "rb"),
                    caption="Image of problem N{}'s answer.".format(problem.index),
                )
                self.unilog("Sending image for problem {}'s answer".format(problem.index))
            except Exception as e:
                self.unilog("Can't send image {} for problem N{}'s answer.".format(
                    image, problem.index))
                print(e)
                logging.info(e)
        self.source.bot.send_message(self.source.participant_group, problem.close(self.source.participant_group))
        t_pages = self.source.participant_group.telegraphpage_set.all()
        if t_pages:  # Create the page manually with DynamicTelegraphPageCreator
            t_page = t_pages[
                len(t_pages) -
                1]  # Using last added page -> negative indexing is not supported
            t_account = t_page.account
            page_controller = DynamicTelegraphPageCreator(t_account.access_token)
            page_controller.load_and_set_page(t_page.path, return_content=False)
            page_controller.update_page(
                content=self.createGroupLeaderBoardForTelegraph(self.source.participant_group))
        self.source.participant_group.activeProblem = None
        self.source.participant_group.save()

    def cancel_problem(self):
        """ Will cancel the problem and remove all answers from the DB.  """
        if self.source.participant_group.activeProblem:
            answers = [answer for answer in Answer.objects.filter(
                group_specific_participant_data__participant_group=self.source.participant_group,
                problem=self.source.participant_group.activeProblem)]
            for answer in answers:
                answer.delete()
            self.source.participant_group.activeSubjectGroupBinding.last_problem = self.source.participant_group.activeProblem.previous
            self.source.participant_group.activeSubjectGroupBinding.save()
            temp_problem = self.source.participant_group.activeProblem
            self.source.participant_group.activeProblem = None
            self.source.participant_group.save()
            self.source.bot.send_message(
                self.source.participant_group,
                "The problem {} is cancelled.".format(temp_problem.index),
                reply_to_message_id=self.source.message['message_id'])
        else:
            self.source.bot.send_message(
                self.source.participant_group,
                "There is not active problem to cancel.",
                reply_to_message_id=self.source.message['message_id'])

    def start_in_participant_group(self):  # Won't work in new groups
        """ Will create bot bindings with a given group """
        binding = BotBinding(bot=self.source.bot, participant_group=self.source.participant_group)
        binding.save()
        self.source.bot.send_message(
            self.source.participant_group,
            "This participant_group is now bound with me, to break the connection, use /stop command.",
            reply_to_message_id=self.source.message["message_id"],
        )

    def remove_from_participant_group(self):
        """ Will remove bot binding with a given group """
        self.source.bot.botbinding_set.objects.get(bot=self.source.bot).delete()
        self.source.bot.send_message(
            self.source.participant_group,
            "The connection was successfully stopped.",
            reply_to_message_id=self.source.message["message_id"],
        )

    def add_subject(self):
        """ Will add subject to the group and select it if the group doesn't have active subject """
        pass

    def select_subject(self):
        """ Will select subject in the group
        Give with message
         - index
        """
        if not ' ' in self.source.raw_text or not self.source.raw_text.split(' ')[1].isnumeric():
            self.source.bot.send_message(
                self.source.participant_group,
                """You have to give the index of subject to select.\nYou can get indexes with /subjects_list command.""",
                reply_to_message_id=self.source.message['message_id'])
            return
        index = int(self.source.raw_text.split(' ')[1])
        subject_group_bindings = self.source.participant_group.subjectgroupbinding_set.all()
        if index not in range(1, len(subject_group_bindings) + 1):
            self.source.bot.send_message(
                self.source.participant_group,
                """You have to give valid subject index.\nYou can get indexes with /subjects_list command.""",
                reply_to_message_id=self.source.message['message_id'])
            return
        self.source.participant_group.activeSubjectGroupBinding = subject_group_bindings[index
                                                                                         - 1]
        self.source.participant_group.activeProblem = None
        self.source.participant_group.save()
        self.source.bot.send_message(
            self.source.participant_group,
            """Subject "{}" is now selected.""".format(
                subject_group_bindings[index - 1].subject.name),
            reply_to_message_id=self.source.message['message_id'])

    def active_subject(self):
        """ Will send active subject to the group if available """
        if self.source.participant_group.activeSubjectGroupBinding:
            self.source.bot.send_message(
                self.source.participant_group,
                """Subject "{}" is active.""".format(
                    self.source.participant_group.activeSubjectGroupBinding.subject.name),
                reply_to_message_id=self.source.message['message_id'])
        else:
            self.source.bot.send_message(
                self.source.participant_group,
                """There is no active subject in this group.""",
                reply_to_message_id=self.source.message['message_id'])

    def finish_subject(self):
        """ Will close subject in the group """
        pass

    def get_subjects_list(self):
        """ Will send subjects list for current group """
        self.source.bot.send_message(
            self.source.participant_group,
            """This is the subjects list for current group:\n{}""".format('\n'.join(
                ' - '.join(str(e) for e in el)
                for el in enumerate((binding.subject.name
                                     for binding in self.source.participant_group.
                                    subjectgroupbinding_set.all()), 1))),
            reply_to_message_id=self.source.message['message_id'])

    def get_score(self):
        """ Will send the score of the participant to the group """
        participant = Participant.objects.filter(pk=self.source.message["from"]["id"])
        if participant:
            participant = participant[0]
            specific = GroupSpecificParticipantData.objects.filter(
                participant=participant, participant_group=self.source.participant_group)
            if specific:
                specific = specific[0]
                self.source.bot.send_message(
                    self.source.participant_group,
                    "{}'s score is {}".format(str(participant), specific.score),
                    reply_to_message_id=self.source.message["message_id"],
                )

    def report(self):
        """ Temp -> Will be created """
        pass

    def add_user_defined_problem(self):
        """ Add User-defined Problem """
        pass

    def start_in_administrator_page(self):
        """ Will save administrator page """
        administrator_page = AdministratorPage(
            telegram_id=self.source.message["chat"]["id"],
            username=self.source.message["chat"].get("username"),
            title=self.source.message["chat"].get("title"),
            type=(GroupType.objects.filter(name=self.source.message["chat"].get("type"))
                  or [None])[0],
        )
        administrator_page.save()
        self.source.bot.send_message(
            administrator_page,
            "Congratulations, this group is now registered as an administrator page.",
            reply_to_message_id=self.source.message['message_id'])

    def stop_in_administrator_page(self):
        """ Will remove administrator page """
        chat_id = self.source.administrator_page.telegram_id
        self.source.administrator_page.delete()
        self.source.bot.send_message(
            chat_id,
            'This target is no longer an administrator page, so you won\'t get any log here anymore.',
            reply_to_message_id=self.source.message['message_id'])


    def status_in_administrator_page(self) -> None:
        """ Will log the status to the administrator page """
        try:
            answers = self.source.administrator_page.participant_group.activeProblem.answer_set.filter(
                processed=False,
                group_specific_participant_data__participant_group=
                self.source.administrator_page.participant_group)
        except AttributeError:  # If there is no active problem
            self.source.bot.send_message(
                self.source.administrator_page,
                """There is no active problem.""",
                reply_to_message_id=self.source.message['message_id'])
            return
        answers_count = [el for el in ((
            variant,
            len([answer for answer in answers
                 if answer.answer.upper() == variant]))
            for variant in 'ABCDE') if el[1]]
        self.source.bot.send_message(
            self.source.administrator_page,
            """Current status for problem {} is{}\nFor more contact with @KoStard""".format(
                self.source.administrator_page.participant_group.activeProblem.index,
                ''.join('\n{} - {}'.format(*el) for el in answers_count)
                if answers_count else ' - No one answered.'),
            reply_to_message_id=self.source.message['message_id'])


    def root_test(self) -> None:
        """ This is used for some root testings of the bot """
        ### Now will be used for image sending test
        try:
            self.source.bot.send_image(
                self.source.administrator_page,
                open('../media/images/Photos/image005.png', 'rb'),
                reply_to_message_id=self.source.message['message_id']
            )  # Is working, so the bug with image sending is solved.
        except Exception as e:
            print(e)
            self.unilog("Can't send image in root_test")


    def register_participant_group(self):
        """ Will register chat as a participant group """
        chat = self.source.message.get("chat")
        tp = get_from_Model(GroupType, name=chat['type'])
        if not chat:
            logging.info("Can't get chat to register.")
            pass
        participant_group = get_from_Model(
            ParticipantGroup, telegram_id=chat['id'])
        if participant_group:
            self.source.bot.send_message(
                participant_group,
                "This group is already registered.",
                reply_to_message_id=self.source.message['message_id']
            )  # Maybe add reference to the documentation with this message
        elif not tp:
            self.source.bot.send_message(
                chat['id'],
                "Unknown type of group, to improve this connect with @KoStard.",
                reply_to_message_id=self.source.message['message_id'])
        else:
            participant_group = ParticipantGroup(
                telegram_id=chat['id'],
                username=chat.get('username'),
                title=chat.get('title'),
                type=tp)
            participant_group.save()
            binding = BotBinding(bot=self.source.bot, participant_group=participant_group)
            binding.save()
            self.source.bot.send_message(
                participant_group,
                """This group is now registered and a binding is created,\
so now the bot will listen to your commands.""",
                reply_to_message_id=self.source.message['message_id'])


    def handle_restart_command(self):
        """
        Will restart the script
        - Maybe will result to problems when in multi-bot mode, because will restart the program, while other
            bot's commands are being processed
        """
        self.unilog("Has to restart")
        add_to_post_processing_stack(self.bot, update_and_restart)


    def createGroupLeaderBoard(self):
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
            (gs for gs in self.source.participant_group.groupspecificparticipantdata_set.all()
             if gs.score),
            key=lambda gs: [gs.score, gs.percentage],
        )[::-1]]
        return gss


    def get_promoted_participants_list_for_leaderboard(self):
        """ Will process data of promoted participants for group leaderboards """
        admin_gss = [{
            "participant":
                gs.participant,
            "non_standard_role":
                gs.highest_non_standard_role_binding.role,
        } for gs in sorted(
            (gs for gs in self.source.participant_group.groupspecificparticipantdata_set.all()
             if gs.highest_non_standard_role_binding),
            key=
            lambda gs: [gs.highest_non_standard_role_binding.role.priority_level],
        )[::-1]]
        return admin_gss


    def createGroupLeaderBoardForTelegraph(self,
                                           *,
                                           max_limit=0):
        """ Will create content for leaderboard telegraph page """
        raw_leaderboard = self.createGroupLeaderBoard(self.source.participant_group)
        raw_promoted_list = self.get_promoted_participants_list_for_leaderboard(
            self.source.participant_group)
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
