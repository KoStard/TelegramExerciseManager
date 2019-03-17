from main.models import *
from main.universals import get_response, configure_logging, safe_getter, get_from_Model, update_and_restart
from main.dynamic_telegraph_page_creator import DynamicTelegraphPageCreator
from django.utils import timezone
from time import sleep
from datetime import datetime
import logging
from .source_manager import SourceManager
from .commands_mapping import COMMANDS_MAPPING
from .message_handlers import message_handler
from .message_handlers.user_pg_message_bindings_handler import AVAILABLE_MESSAGE_BINDINGS

"""
Will contain some function relations and arguments to run them after a command is processed
{bot_object_id: [{func: f, args: [], kwargs: {}}]}
"""
POST_PROCESSING_STACK = {}


# configure_logging()


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


def register_groupspecificparticipantdata(**kwargs
                                          ) -> GroupSpecificParticipantData:
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
    """
    The main worker class - bot-specific
    """
    COMMANDS_MAPPING = COMMANDS_MAPPING

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
            if self.pg_adm_page:
                self.bot.send_message(self.pg_adm_page, message)
        elif isinstance(self.participant_group,
                        AdministratorPage) or self.administrator_page:
            self.bot.send_message(
                self.participant_group or self.administrator_page,
                message,
                reply_to_message_id=self.message['message_id'])
        else:
            print("Unknown in adm_log!!!")

    def run_post_processing_functions(self):
        # Can't be sourced, because this has to be called after the bot's offset is changed
        if self.bot.id not in POST_PROCESSING_STACK:
            return
        funcs = POST_PROCESSING_STACK[self.bot.id]
        del POST_PROCESSING_STACK[self.bot.id]
        for func_data in funcs:
            func_data['func'](*(func_data.get('args') or []),
                              **(func_data.get('kwargs') or {}))

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
            update=update, message=message,
            bot=self.bot)  # Adding the dictionary for this update
        catched_exception = False
        self.source.message = message
        if message:
            try:
                message_handler.handle_message(self)
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
        if self.source.is_superadmin:
            pr_m = 'СЂСџРЉвЂ№'
        elif self['groupspecificparticipantdata'].is_admin:
            pr_m = 'СЂСџвЂєРЋРїС‘РЏ'
        else:
            pr_m = 'РІВ­С’' * max(
                self['groupspecificparticipantdata'].
                    highest_standard_role_binding.role.priority_level, 0)

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
        ) or (("New chat member" if len(
            self['message']['new_chat_members']) == 1 and self['message']
                                    ['new_chat_members'][0]['id'] == self['message']['from']['id']
               else 'Invited {}'.format(', '.join(
            user['first_name'] or user['last_name'] or user['username']
            for user in self['message'].get('new_chat_members'))))
              if 'new_chat_members' in self['message'] else '')
        result = f"{pr_m}{name} -> {data}"
        return result

    def _get_unilog_message_identifier(self) -> str:
        """
        Will return identifier for the unilogs.
        - {group title} when in participant group
        - UR {group title} when in unregistered group
        - PRIVATE when in private mode
        - '' else
        """
        if not self.source.get('message'):
            return ''
        if self.source.get('participant_group'):
            return f'{self.source.participant_group.username or self.source.participant_group.title} '
        elif self.source.get('administrator_page'):
            return f'ADMP {self.source.administrator_page.username or self.source.administrator_page.title} '
        elif self.source.message['chat']['type'] in ('group', 'supergroup'):
            return f'UR {self.source.message["chat"].get("username") or self.source.message["chat"].get("title")} '
        elif self.source.message['chat']['type'] in ('private',):
            return f'PRIVATE '
        return ''

    def unilog(self, log: str, *, to_participant_group=False) -> None:
        """ Will log to the:
        - stdout
        - logging
        - adm_page
        """
        identifier = self._get_unilog_message_identifier()
        print(f'{identifier}{log}')  # Logging to stdout
        logging.info(
            f'{timezone.now()} | {identifier}{log}')  # Logging to logs file
        self.adm_log(log)  # Logging to administrator page
        if to_participant_group:
            self.bot.send_message(
                self.participant_group,
                log,
                reply_to_message_id=self.message['message_id'])

    def answer_to_the_message(self, text: str):
        """
        Will answer to the message
        """
        self.bot.send_message(
            self.message['chat']['id'],
            text,
            reply_to_message_id=self.message['message_id'])

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
        gss = [
            {
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
                "position_change":
                    self.source.position_change.get(gs.id, 0)
            } for gs in sorted(
                (gs for gs in (self.source.participant_group or self.source.administrator_page.participant_group).
                    groupspecificparticipantdata_set.all() if gs.score),
                key=lambda gs: (-(gs.score or 0), -(gs.percentage or 0), gs.id),
                # In the beginning higher score, higher percentage and lower id
            )
        ]
        return gss

    def get_promoted_participants_list_for_leaderboard(self):
        """ Will process data of promoted participants for group leaderboards """
        admin_gss = [{
            "participant":
                gs.participant,
            "non_standard_role":
                gs.highest_non_standard_role_binding.role,
        } for gs in sorted(
            (gs for gs in (self.source.participant_group or self.source.administrator_page.participant_group).
                groupspecificparticipantdata_set.all()
             if gs.highest_non_standard_role_binding),
            key=lambda gs:
            [gs.highest_non_standard_role_binding.role.priority_level],
        )[::-1]]
        return admin_gss

    def createGroupLeaderBoardForTelegraph(self, *, max_limit=0):
        """ Will create content for leaderboard telegraph page """
        raw_leaderboard = self.createGroupLeaderBoard()
        raw_promoted_list = self.get_promoted_participants_list_for_leaderboard(
        )
        res = []

        res.append(
            DynamicTelegraphPageCreator.create_blockquote([
                "Here you see dynamically updating Leaderboard of ",
                DynamicTelegraphPageCreator.create_link(
                    (self.source.participant_group or self.source.administrator_page.participant_group).title,
                    f'https://t.me/{(self.source.participant_group or self.source.administrator_page.participant_group).username}' if (
                                self.source.participant_group or self.source.administrator_page.participant_group).username else ''),
                '.\n',
                "This is a part of ",
                DynamicTelegraphPageCreator.create_link(
                    "MedStard", "https://t.me/MedStard"),
                ", where you can find much more stuff related to medicine and education, so welcome to our community."
            ]))

        last_role = None
        roles_index = 0
        current_list = None
        for gs in (raw_leaderboard[:max_limit]
        if max_limit else raw_leaderboard):

            # Creating position change identifier
            position_change_identifier = ''
            if gs['position_change'] > 0:
                position_change_identifier = 'СЂСџвЂќС�'
            elif gs['position_change'] < 0:
                position_change_identifier = 'СЂСџвЂќР…'

            if not last_role or gs['standard_role'].value != last_role.value:
                if last_role:
                    res.append(DynamicTelegraphPageCreator.hr)
                roles_index += 1
                res.append(
                    DynamicTelegraphPageCreator.create_title(
                        4, '{}. {} {}'.format(
                            roles_index, gs['standard_role'].name,
                            'РІВ­С’' * gs['standard_role'].priority_level)))
                ordered_list = DynamicTelegraphPageCreator.create_ordered_list(
                )
                res.append(ordered_list)
                current_list = ordered_list['children']
                last_role = gs['standard_role']
            if roles_index == 1:
                current_list.append(
                    DynamicTelegraphPageCreator.create_list_item([
                        DynamicTelegraphPageCreator.create_bold([
                            DynamicTelegraphPageCreator.create_code([
                                DynamicTelegraphPageCreator.create_bold(
                                    position_change_identifier +
                                    '{}'.format(gs['score'])), 'xp{}'.format(
                                    (' [{}%]'.format(gs['percentage']) if
                                     gs['percentage'] is not None else ''))
                            ]), ' - {}'.format(gs['participant'].full_name)
                        ])
                    ]))
            else:
                current_list.append(
                    DynamicTelegraphPageCreator.create_list_item([
                        DynamicTelegraphPageCreator.create_code([
                            DynamicTelegraphPageCreator.create_bold(
                                position_change_identifier +
                                '{}'.format(gs['score'])), 'xp{}'.format(
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
                                gs['participant'].username))
                        if gs['participant'].username else
                        gs['participant'].full_name
                    ])))
        return res

    def create_and_save_telegraph_page(
            self,
            t_account: TelegraphAccount,
            title: str,
            content: list,
            participant_group: ParticipantGroup = None) -> DynamicTelegraphPageCreator:
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
