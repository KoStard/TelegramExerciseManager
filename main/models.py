from django.db import models
from django.utils import timezone
from main.universals import (get_response, configure_logging, safe_getter)
import io
import re
import logging
from main.universals import get_from_Model

configure_logging()

MESSAGE_MAX_LENGTH = 4096


class Discipline(models.Model):
    """ Discipline model """
    name = models.CharField(max_length=70)
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Discipline'
        db_table = 'db_discipline'


class Subject(models.Model):
    """ Subject model """
    name = models.CharField(max_length=70)
    value = models.CharField(max_length=100)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)

    def __len__(self):
        return self.problem_set.count()

    def __str__(self):
        return '{}->{}'.format(self.discipline, self.name)

    class Meta:
        verbose_name = 'Subject'
        db_table = 'db_subject'


class Problem(models.Model):
    """ Problem model -> for now has fixed variants - A, B, C, D, E """

    index = models.IntegerField(null=True, blank=True)
    formulation = models.CharField(max_length=1500)
    variant_a = models.CharField(max_length=300)
    variant_b = models.CharField(max_length=300)
    variant_c = models.CharField(max_length=300)
    variant_d = models.CharField(max_length=300)
    variant_e = models.CharField(max_length=300)
    answer_formulation = models.CharField(max_length=6000)
    right_variant = models.CharField(max_length=1)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    is_special = models.BooleanField(default=False)
    value = models.IntegerField(default=50)
    chapter = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return """\\<b>#Problem N{}\\</b>{}\n{}{}{}""".format(
            self.index, ("\nFrom chapter: #{}".format(
                self.chapter.replace(' ', '_').replace(':', '')) if self.chapter else ''),
            self.formulation,
            ''.join(f'\n{variant.upper()}. {getattr(self, f"variant_{variant.lower()}")}' if getattr(self,
                                                                                                     f"variant_{variant.lower()}") != "[[EMPTY]]" else ""
                    for variant in 'abcde'),
            ('' if self.has_next else '\n#last'))

    def get_answer(self):
        """ Is generating problem answer formulation to publish """
        return """\\<b>The right choice is {}\\</b>\n{}\n#Answer to {}\n""".format(
            self.right_variant.upper(), self.answer_formulation, self.index)

    def close(self, participant_group):
        """ Will close the problem for participant group """
        answers = sorted(
            self.answer_set.filter(
                group_specific_participant_data__participant_group=
                participant_group,
                processed=False),
            key=lambda answer: answer.id
        )  # Getting both right and wrong answers -> have to be processed
        for answer in answers:
            answer.process()
            answer.group_specific_participant_data.recalculate_roles()
        return self.get_leader_board(
            participant_group,
            answers=[answer for answer in answers if answer.right
                     ])  # Including in the leaderboard only right answers

    def get_leader_board(self, participant_group, answers=None):
        """ Will return problem leaderboard """
        answers = answers or sorted(
            Answer.objects.filter(
                problem=self,
                group_specific_participant_data__participant_group=
                participant_group,
                right=True,
                processed=False),
            key=lambda answer: answer.id)
        res = "Right answers:"
        if len(answers):
            index = 1
            for answer in answers:
                current = "{}: {} - {}{}".format(
                    index, answer.group_specific_participant_data.participant,
                    answer.group_specific_participant_data.score,
                    (' [{}%]'.format(
                        answer.group_specific_participant_data.percentage)
                     if answer.group_specific_participant_data.percentage else
                     ''))
                if index <= 3:
                    current = '\\<b>{}\\</b>'.format(current)
                index += 1
                res += '\n' + current
        else:
            res += '\nNo one solved the problem. #Hardcore'
        res += '\n#Problem_Leaderboard'
        return res

    @property
    def next(self):
        """ Will return next problem if available """
        if self.subject and self.index < len(self.subject):
            n = self.subject.problem_set.filter(index=self.index + 1)
            if n:
                return n[0]

    @property
    def has_next(self):
        """ Will check if has next problem """
        return self.subject and self.index < len(self.subject)

    @property
    def previous(self):
        """ Will return previous problem if available """
        if self.subject and self.index > 1:
            n = self.subject.problem_set.filter(index=self.index - 1)
            if n:
                return n[0]

    @staticmethod
    def get_list_display():
        """ Used in the django_admin_creator """
        return (
            'index',
            'formulation',
            'right_variant',
            'subject',
            'chapter',
            'is_special',
            'value',
        )

    class Meta:
        verbose_name = 'Problem'
        db_table = 'db_problem'


class ParticipantDefinedProblem(Problem):
    """ Participant-defined problem """
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE)
    problem_name = models.CharField(max_length=50)

    def __str__(self):
        return """\\<b>#User_Defined_Problem {} - From #{}\\</b>\n{}\nA. {}\nB. {}\nC. {}\nD. {}\nE. {}""".format(
            self.problem_name, self.participant.name.replace(' ', '_'),
            self.formulation, self.variant_a, self.variant_b, self.variant_c,
            self.variant_d, self.variant_e)

    @staticmethod
    def get_list_display():
        """ Used in the django_admin_creator """
        return (
            'problem_name',
            'participant',
            'formulation',
            'right_variant',
            'value',
        )

    class Meta:
        verbose_name = 'Participant-defined Problem'
        db_table = 'db_problem_participant_defined'


class ProblemImage(models.Model):
    """ Problem Image Model """
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    image = models.ImageField()
    for_answer = models.BooleanField(default=False)

    def __str__(self):
        return f'{"A" if self.for_answer else "P"}: {self.image} -> {self.problem}'

    class Meta:
        verbose_name = 'Problem Image'
        db_table = 'db_problem_image'


class GroupType(models.Model):
    """ Group Types """
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    @property
    def value(self):
        """ Will return standardized name as value """
        return re.sub('\s+', '_', self.name.lower().strip())

    class Meta:
        verbose_name = 'Group Type'
        db_table = 'db_group_type'


class Group(models.Model):
    """ Group model """

    telegram_id = models.CharField(max_length=50)
    username = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=150)
    type = models.ForeignKey(GroupType, on_delete=models.CASCADE)

    def __str__(self):
        return '[{}] {}'.format(self.type.name, self.title or self.username)

    class Meta:
        verbose_name = 'Group'
        db_table = 'db_group'


class ParticipantGroupPlayingModePrincipal(models.Model):
    """ Participant Group Playing Mode Principal Model """
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Participant Group Playing Mode Principal'
        db_table = 'db_participant_group_playing_mode_principal'


class ParticipantGroupPlayingMode(models.Model):
    """ Participant Group Playing Mode Model """
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    principal = models.ForeignKey(
        ParticipantGroupPlayingModePrincipal,
        on_delete=models.CASCADE,
        blank=True,
        null=True)
    data = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return '{} -[{}]-> {}'.format(self.name, self.principal, self.data)

    class Meta:
        verbose_name = 'Participant Group  Playing Mode'
        db_table = 'db_participant_group_playing_mode'


class ParticipantGroup(Group):
    """ Participant Group model """
    activeProblem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, blank=True, null=True)
    activeSubjectGroupBinding = models.ForeignKey(
        'SubjectGroupBinding', on_delete=models.CASCADE, blank=True, null=True)
    playingMode = models.ForeignKey(
        ParticipantGroupPlayingMode, on_delete=models.CASCADE)

    def get_administrator_page(self):
        """ Will return administrator page if available """
        return safe_getter(self, 'administratorpage')

    @staticmethod
    def get_list_display():
        """ Used in the django_admin_creator """
        return ("telegram_id", "username", "title", "type",
                ("active_problem", "self.activeProblem.index"),
                ("active_subject_group_binding",
                 "self.activeSubjectGroupBinding"), "playingMode")

    def __str__(self):
        return '[{}] {} -[{}::{}]-> {}'.format(
            self.type.name, self.title or self.username, self.playingMode,
            safe_getter(self, 'activeSubjectGroupBinding.subject', default=''),
            safe_getter(self, 'activeProblem.index', default=''))

    def save(self, *args, **kwargs):
        if not hasattr(self, 'playingMode') or not self.playingMode:
            self.playingMode = ParticipantGroupPlayingMode.objects.get(
                value='default')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Participant Group'
        db_table = 'db_participant_group'


class AdministratorPage(Group):
    """ Administrator Page model """

    participant_group: ParticipantGroup = models.OneToOneField(
        ParticipantGroup, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return 'ADMINISTRATOR PAGE FOR {}'.format(self.participant_group)

    class Meta:
        verbose_name = 'Administrator Page'
        db_table = 'db_administrator_page'


class User(models.Model):
    """ User model """
    # Use id as telegram_id
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)

    @property
    def name(self):
        """ Universal method to get available name of the user """
        return self.first_name or self.username or self.last_name

    @property
    def full_name(self):
        """ Universal method to get full name of the user """
        if self.first_name or self.last_name:
            return ' '.join(n for n in (self.first_name, self.last_name) if n)
        else:
            return self.username

    def update_from_telegram_dict(self, user: dict):
        """ Will update username, first_name and last_name from given user dict """
        self.username = user.get('username')
        self.first_name = user.get('first_name')
        self.last_name = user.get('last_name')
        self.save()

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        verbose_name = 'User'
        db_table = 'db_user'


class Bot(User):
    """ Bot model 
     - for_testing - if is True, will be used in testing mode
    """
    token = models.CharField(max_length=50)
    offset = models.IntegerField(default=0)
    last_updated = models.DateTimeField(blank=True, null=True)
    for_testing = models.BooleanField(default=False)

    @property
    def base_url(self):
        """ This is the base URL of the bot for all API calls """
        return 'https://api.telegram.org/bot{}/'.format(self.token)

    def update_information(self):
        """ Bot will update it's information with getMe """
        url = self.base_url + 'getMe'
        resp = get_response(url)
        if resp:
            self.username = resp.get('username')
            self.first_name = resp.get('first_name')
            self.last_name = resp.get('last_name')
            self.save()

    def get_group_member(self, participant_group, participant):
        """ Will find a group member and return if available """
        if isinstance(participant_group, Group):
            participant_group = participant_group.telegram_id
        if isinstance(participant, Participant):
            participant = participant.id
        url = self.base_url + 'getChatMember'
        payload = {'chat_id': participant_group, 'user_id': participant}
        return get_response(url, payload=payload)

    def send_message(self,
                     group: 'text/id or group',
                     text,
                     *,
                     parse_mode='HTML',
                     reply_to_message_id=None):
        """ Will send a message to the group """
        if not (isinstance(group, str) or isinstance(group, int)):
            group = group.telegram_id

        if parse_mode == 'Markdown':
            text = text.replace('_', '\_')
        blocks = []
        if len(text) > MESSAGE_MAX_LENGTH:
            current = text
            while len(current) > MESSAGE_MAX_LENGTH:
                f = current.rfind('. ', 0, MESSAGE_MAX_LENGTH)
                blocks.append(current[:f + 1])
                current = current[f + 2:]
            blocks.append(current)
        else:
            blocks.append(text)
        resp = []
        for message in blocks:
            url = self.base_url + 'sendMessage'
            payload = {
                'chat_id':
                    group,
                'text':
                    message.replace('<', '&lt;').replace('\\&lt;', '<'),
                'reply_to_message_id':
                    reply_to_message_id if not resp else resp[-1].get('message_id')
            }
            if parse_mode:
                payload['parse_mode'] = parse_mode
            resp_c = get_response(url, payload=payload)
            logging.info(resp_c)
            resp.append(resp_c)
        return resp

    def send_image(self,
                   participant_group: 'text/id or group',
                   image_file: io.BufferedReader,
                   *,
                   caption='',
                   reply_to_message_id=None):
        """ Will send an image to the group """
        if not (isinstance(participant_group, str)
                or isinstance(participant_group, int)):
            participant_group = participant_group.telegram_id
        url = self.base_url + 'sendPhoto'
        payload = {
            'chat_id': participant_group,
            'caption': caption,
            'reply_to_message_id': reply_to_message_id,
        }
        files = {'photo': image_file}
        resp = get_response(url, payload=payload, files=files)
        logging.info(resp)
        return resp

    def delete_message(self, participant_group: str or Group, message_id: int
                                                                          or str):
        """ Will delete message from the group """
        if not (isinstance(participant_group, str)
                or isinstance(participant_group, int)):
            participant_group = participant_group.telegram_id
        url = self.base_url + 'deleteMessage'
        payload = {'chat_id': participant_group, 'message_id': message_id}
        resp = get_response(url, payload=payload)
        logging.info(resp)
        return resp

    def __str__(self):
        return '[BOT] {}'.format(self.first_name or self.username
                                 or self.last_name)

    class Meta:
        verbose_name = 'Bot'
        db_table = 'db_bot'


class Participant(User):
    """ Participant model """
    sum_score = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Participant'
        db_table = 'db_participant'


class SuperAdmin(models.Model):
    """ Super-Admin model """

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return '{{Super-Admin}} {}'.format(self.user)

    class Meta:
        verbose_name = 'Super Admin'
        db_table = 'db_super_admin'


class Role(models.Model):
    """ Role """
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    priority_level = models.IntegerField(default=1)
    from_stardard_kit = models.BooleanField(default=False)

    def __lt__(self, other: 'Role'):
        return self.priority_level < other.priority_level

    def __gt__(self, other: 'Role'):
        return self.priority_level > other.priority_level

    def __le__(self, other: 'Role'):
        return self.priority_level <= other.priority_level

    def __ge__(self, other: 'Role'):
        return self.priority_level >= other.priority_level

    def __eq__(self, other: 'Role'):
        return self.priority_level == other.priority_level

    def __str__(self):
        return '[{}] {}'.format(self.priority_level, self.name)

    class Meta:
        verbose_name = 'Role'
        db_table = 'db_role'


class ScoreThreshold(models.Model):
    """ Score threshold """
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    range_min = models.IntegerField()
    range_max = models.IntegerField()

    def __str__(self):
        return '{} [{}; {}]'.format(self.role.name, self.range_min,
                                    self.range_max)

    class Meta:
        verbose_name = 'Score Threshold'
        db_table = 'db_score_threshold'


class GroupSpecificParticipantData(models.Model):
    """ Group-specific participant data """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    participant_group = models.ForeignKey(
        ParticipantGroup, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    joined = models.DateTimeField(blank=True, null=True)

    @property
    def percentage(self):
        """ Will return user percentage if the score is higher or equal to 450 """
        if self.score >= 450:
            return round((1 - sum(
                answer.problem.value
                for answer in self.answer_set.filter(right=False)) / self.score
                          ) * 1000) / 10

    def recalculate_roles(self):
        """ Will recalculate user's roles in the group """
        standard_bindings = [
            b for b in self.participantgroupbinding_set.all()
            if b.role.from_stardard_kit
        ]
        if len(standard_bindings) >= 1:
            highest_binding = sorted(
                standard_bindings,
                key=lambda binding: binding.role.priority_level)[-1]
            for binding in standard_bindings:
                if binding != highest_binding:
                    binding.delete()
            standard_role = highest_binding.role

            new_role = [
                st.role for st in ScoreThreshold.objects.all()
                if st.range_min <= self.score and st.range_max >= self.score
                   and st.role.from_stardard_kit
            ]
            if not new_role or new_role[
                0].priority_level <= standard_role.priority_level:
                return
            new_role = new_role[0]
            if new_role.priority_level == -1:
                return
            # If the participant got to the new level, then setting new role for the binding
            highest_binding.role = new_role
            highest_binding.save()
        else:
            standard_role = None
            new_role = [
                st.role for st in ScoreThreshold.objects.all()
                if st.range_min <= self.score and st.range_max >= self.score
                   and st.role.from_stardard_kit
            ]
            if not new_role:
                return
            new_role = new_role[0]
            if new_role.priority_level == -1:
                return

            # Creating new binding
            ParticipantGroupBinding(
                groupspecificparticipantdata=self, role=new_role).save()
        logging.info('New Role for {} will be {} - score is {}'.format(
            self.participant.name, new_role, self.score))

    @property
    def highest_role_binding(self):
        """ Will return user's highest role binding in the group """
        from main.models import ParticipantGroupBinding
        res = ParticipantGroupBinding(
            groupspecificparticipantdata=self,
            role=Role.objects.get(value='guest'))
        for binding in self.participantgroupbinding_set.all():
            if not res or binding.role.priority_level > res.role.priority_level:
                res = binding
        return res

    @property
    def highest_role(self):
        """ Will return user's highest role in the group """
        return self.highest_role_binding.role or Role.objects.get(
            value='guest')

    @property
    def highest_standard_role_binding(self):
        """ Will return user's highest standard role binding in the group """
        from main.models import ParticipantGroupBinding
        res = ParticipantGroupBinding(
            groupspecificparticipantdata=self,
            role=Role.objects.get(value='guest'))
        for binding in self.participantgroupbinding_set.filter(
                role__from_stardard_kit=True):
            if not res or binding.role.priority_level > res.role.priority_level:
                res = binding
        return res

    @property
    def highest_non_standard_role_binding(self) -> 'ParticipantGroupBinding':
        """ Will return user's highest non-standard role binding in the group """
        res = None
        for binding in self.participantgroupbinding_set.filter(
                role__from_stardard_kit=False):
            if not res or binding.role.priority_level > res.role.priority_level:
                res = binding
        return res

    @property
    def is_admin(self) -> bool:
        """
        Will return True if the participant is admin in current group
        """
        ns_role_binding = self.highest_non_standard_role_binding
        return ns_role_binding and ns_role_binding.role >= Role.objects.get(
            value='admin')  # Will raise error if the database is not filled

    def create_violation(self, type, date=None):
        """ Will create a violation to this GroupSpecificParticipantData """
        violation = Violation(
            groupspecificparticipantdata=self,
            date=date or timezone.now(),
            type=type)
        violation.save()
        return violation

    def __str__(self):
        return '{}-{{{}}}->{}'.format(self.participant, self.score,
                                      self.participant_group)

    class Meta:
        verbose_name = 'Group Specific Participant Data'
        db_table = 'db_group_specific_participant_data'


class ViolationType(models.Model):
    """ Violation types """
    name = models.CharField(max_length=50)
    cost = models.PositiveIntegerField()
    value = models.CharField(max_length=50)

    def __str__(self):
        return '{} [-{}]'.format(self.name, self.cost)

    class Meta:
        verbose_name = 'Violation Type'
        db_table = 'db_violation_type'


class Violation(models.Model):
    """ Participant violation """
    groupspecificparticipantdata = models.ForeignKey(
        GroupSpecificParticipantData, on_delete=models.CASCADE)
    date = models.DateTimeField()
    type = models.ForeignKey(ViolationType, on_delete=models.CASCADE)

    def __str__(self):
        return '{} !!{}!!'.format(self.groupspecificparticipantdata, self.type)

    class Meta:
        verbose_name = 'Violation'
        db_table = 'db_violation'


class ParticipantGroupBinding(models.Model):
    """ Participant-Group binding 
    - Same participant can have multiple bindings in the same group"""
    groupspecificparticipantdata = models.ForeignKey(
        GroupSpecificParticipantData, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def __str__(self):
        return '{}-{{{}}}->{}'.format(
            self.groupspecificparticipantdata.participant, self.role.name,
            self.groupspecificparticipantdata.participant_group)

    def save(self, *args, **kwargs):
        if self.role.value == 'guest':
            return
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Participant-Group Binding'
        db_table = 'db_participant_group_binding'


class BotBinding(models.Model):
    """ Binding of a bot """
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    participant_group = models.ForeignKey(
        ParticipantGroup, on_delete=models.CASCADE)

    def __str__(self):
        return '{}->{}'.format(self.bot, self.participant_group)

    class Meta:
        verbose_name = 'Bot Binding'
        db_table = 'db_bot_binding'


class Answer(models.Model):
    """ User Answer model """

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    answer = models.CharField(max_length=1, null=True, blank=True)
    right = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    group_specific_participant_data = models.ForeignKey(
        GroupSpecificParticipantData, on_delete=models.CASCADE)
    date = models.DateTimeField(blank=True, null=True)

    def process(self):
        """ Will process the answer and give points to the user if is right """
        if not self.processed:
            if self.right:
                self.group_specific_participant_data.score += self.problem.value
                self.group_specific_participant_data.save()
                self.group_specific_participant_data.participant.sum_score += self.problem.value
                self.group_specific_participant_data.participant.save()
            self.processed = True
            self.save()

    def __str__(self):
        return '{}[{}] {} -> Problem {}'.format(
            ("+" if self.right else "-") if self.processed else "*",
            (self.answer.upper() if self.answer else '-'),
            self.group_specific_participant_data, self.problem.index)

    @staticmethod
    def get_list_display():
        """ Used in the django_admin_creator """
        return (
            ("Problem", "self.problem.index"),
            ("Answer", "self.answer.upper() if self.answer else '-'"),
            "right",
            "processed",
            "group_specific_participant_data",
            "date",
        )

    class Meta:
        verbose_name = 'Answer'
        db_table = 'db_answer'


class SubjectGroupBinding(models.Model):
    """ Subject-Group binding """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    participant_group = models.ForeignKey(
        ParticipantGroup, on_delete=models.CASCADE)
    last_problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return '{}->{}'.format(self.subject, self.participant_group)

    @staticmethod
    def get_list_display():
        """ Used in the django_admin_creator """
        return (
            "subject",
            "participant_group",
            ("Last_problem", "self.last_problem.index"),
        )

    class Meta:
        verbose_name = 'Subject-Group Binding'
        db_table = 'db_subject_group_binding'


class TelegramCommand(models.Model):
    """
    Telegram Command Model
    """

    command = models.CharField(max_length=200)
    command_handler = models.CharField(max_length=200)
    minimal_priority_level = models.IntegerField(default=9)
    in_unregistered = models.BooleanField(default=False)
    in_participant_groups = models.BooleanField(default=False)
    in_administrator_pages = models.BooleanField(default=False)
    needs_superadmin = models.BooleanField(default=False)

    def __str__(self):
        return '{} {}_{}{}'.format(self.command, self.minimal_priority_level, ''.join('*' if el else '-' for el in (
            self.in_unregistered, self.in_participant_groups, self.in_administrator_pages)),
                                   'A' if self.needs_superadmin else '-')

    class Meta:
        verbose_name = 'Telegram Command'
        db_table = 'db_telegram_command'


class TelegraphAccount(models.Model):
    """ Telegraph Account model """
    access_token = models.CharField(max_length=70)
    auth_url = models.URLField()

    def __str__(self):
        return '{}'.format(self.access_token)

    class Meta:
        verbose_name = 'Telegraph Account'
        db_table = 'db_telegraph_account'


class TelegraphPage(models.Model):
    """ Telegraph Page model """
    path = models.CharField(max_length=150)
    url = models.URLField()
    account = models.ForeignKey(TelegraphAccount, on_delete=models.CASCADE)
    participant_group = models.ForeignKey(
        ParticipantGroup, on_delete=models.CASCADE, blank=True,
        null=True)  # Maybe we'll create a page without group

    def __str__(self):
        return '{} for {}'.format(self.path, self.participant_group)

    class Meta:
        verbose_name = 'Telegraph Page'
        db_table = 'db_telegraph_page'
