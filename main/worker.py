from main.models import *
from main.universals import get_response, configure_logging, safe_getter, get_from_Model, update_and_restart
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator
from django.utils import timezone
from time import sleep
from datetime import datetime
import logging
from .source_manager import SourceManager
from .commands_mapping import COMMANDS_MAPPING

"""
Will contain some function relations and arguments to run them after a command is processed
{bot_object_id: [{func: f, args: [], kwargs: {}}]}
"""
POST_PROCESSING_STACK = {}

# configure_logging()


AVAILABLE_ENTITIES = {
    "mention": -1,
    "hashtag": 1,
    "cashtag": 0,
    "bot_command": -1,
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
        elif isinstance(self.participant_group, AdministratorPage) or self.administrator_page:
            self.bot.send_message(self.participant_group or self.administrator_page, message,
                                  reply_to_message_id=self.message['message_id'])
        else:
            print("Unknown in adm_log!!!")

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

    def run_command(self, command: TelegramCommand = None):
        if not command:
            command = self.command_model
        COMMANDS_MAPPING[command.command_handler](self)

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

    def unilog(self, log: str, *, to_participant_group=False) -> None:
        """ Will log to the:
        - stdout
        - logging
        - adm_page
        """
        print(log)  # Logging to stdout
        logging.info(f'{timezone.now()} | {log}')  # Logging to logs file
        self.adm_log(log)  # Logging to administrator page
        if to_participant_group:
            self.bot.send_message(self.participant_group, log, reply_to_message_id=self.message['message_id'])

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
            self.source.is_from_superadmin = not not safe_getter(self.participant, 'superadmin')
            return participant
        else:
            self.source.participant = None
            self.source.is_from_superadmin = False
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
        if len(self['text']) == 1 and ((not self.participant_group.activeProblem.variants and self['text'].upper() in (
        'A', 'B', 'C', 'D', 'E')) or (
                                               self.participant_group.activeProblem.variants and self.text.lower() in self.participant_group.activeProblem.variants_dict.keys())):
            self.source.variant = self['text'].upper()
            self.handle_answer()
        else:
            pass  # Just regular message in participant group

    def handle_superadmin_commands_in_pg(self):
        if self.is_from_superadmin:
            if self.command_model.in_participant_groups:
                self.run_command()
            else:
                self.reject_command_in_pg_because_of_source()
        else:
            self.reject_command_in_pg()

    def accept_command_in_pg(self):
        self.run_command()

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

    def reject_command_in_pg_because_of_source(self):
        self.unilog("The command '{}' is not supposed to be used in the Participant Groups.".format(self.command),
                    to_participant_group=True)

    def handle_pgm_commands(self):
        """
        Will handle commands from participant_group message
        """
        if not self['command']:
            return
        if self.command_model:
            priority_level = self.groupspecificparticipantdata.highest_role.priority_level
            if self.command_model.needs_superadmin:  # Got superadmin commands in PG
                self.handle_superadmin_commands_in_pg()  # Not checking permissions, just handling
            else:  # Got regular commands in PG
                if self.is_from_superadmin or priority_level >= self.command_model.minimal_priority_level:
                    if self.command_model.in_participant_groups:
                        self.accept_command_in_pg()
                    else:
                        self.reject_command_in_pg_because_of_source()
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

    def get_message_sender_participant_from_administrator_page(self):
        """
        Will get participant from administrator page message
        """
        if self.source.get('message'):
            participant = get_from_Model(
                Participant, id=self['message']['from']['id'])
            if not participant:
                self.source.participant = None
                self.source.is_from_superadmin = False
                print("Can't find participant {}".format(
                    self.message['from']['first_name'] or self.message['from']['username'] or self.message['from'][
                        'last_name']))
                return
            self.source.participant = participant
            self.source.is_from_superadmin = not not safe_getter(self.participant, 'superadmin')
            return participant
        else:
            self.source.participant = None
            self.source.is_from_superadmin = False
            raise ValueError("INVALID MESSAGE DATA")

    def get_groupspecificparticipantdata_of_active_participant_from_administrator_page(self):
        """
        Will get groupspecificparticipantdata from administrator page and participant
        """
        self.groupspecificparticipantdata = get_from_Model(self.participant.groupspecificparticipantdata_set,
                                                           _mode='direct',
                                                           participant_group__administratorpage=self.administrator_page)

    def reject_command_in_administrator_page(self):
        self['bot'].send_message(
            self.administrator_page,
            ('Sorry dear {}, you don\'t have permission to use ' +
             'command "{}" - your highest role is "{}".').format(
                self['participant'], self['command'],
                self['groupspecificparticipantdata'].highest_role.name),
            reply_to_message_id=self['message']["message_id"],
        )

    def reject_command_in_administrator_pages_because_of_source(self):
        self.unilog("The command '{}' is not supposed to be used in the Administrator Pages.".format(self.command))

    def handle_message_from_administrator_page(self):
        """ Will handle message from administrator page
        + superadmins """
        if not self['command']:
            return  # Just text
        if self.command_model:
            self.get_message_sender_participant_from_administrator_page()
            if not self.participant:
                self.unilog("Unknown user in the administrator page.")
                return
            if not self.is_from_superadmin and not self.command_model.needs_superadmin:
                self.get_groupspecificparticipantdata_of_active_participant_from_administrator_page()
                priority_level = self.groupspecificparticipantdata.highest_role.priority_level
            if self.is_from_superadmin or (
                    not self.command_model.needs_superadmin and priority_level >= self.command_model.minimal_priority_level):
                if not self.command_model.in_administrator_pages:
                    self.reject_command_in_administrator_pages_because_of_source()
                    return
                self.run_command()
            else:
                self.reject_command_in_administrator_page()
        else:
            self['bot'].send_message(
                self['administrator_page'],
                "Invalid command.",
                reply_to_message_id=self['message']['message_id'])

    def handle_message_from_superadmin_in_unregistered_group(self):
        """ Will handle message from superadmin
        that are not in the administrator page """
        if self.command_model.in_unregistered:
            self.run_command()

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
        if self.source.command:
            self.source.command_model = get_from_Model(TelegramCommand, command=self.command)

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
            self.handle_message_from_superadmin_in_unregistered_group()
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

    def add_to_post_processing_stack(self, func, *args, **kwargs):
        """
        :param bot: current bot object
        :param func: has to be either function or dict with func key that relates to a function
        :param args: has to be used when the func is function
        :param kwargs: has to be used when the func is function
        :return:
        """
        if self.source.bot.id not in POST_PROCESSING_STACK:
            POST_PROCESSING_STACK[self.source.bot.id] = []
        if isinstance(func, dict):
            POST_PROCESSING_STACK[self.source.bot.id].append(func)
        else:
            POST_PROCESSING_STACK[self.source.bot.id].append({
                'func': func,
                'args': args,
                'kwargs': kwargs
            })

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
