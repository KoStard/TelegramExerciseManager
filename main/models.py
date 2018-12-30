from django.db import models
from main.universals import (
    get_request,
    configure_logging,
)
import io
import re
import logging
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

    def __str__(self):
        return '{}->{}'.format(self.discipline, self.name)

    class Meta:
        verbose_name = 'Subject'
        db_table = 'db_subject'


class Problem(models.Model):
    """ Problem model """

    index = models.IntegerField(null=True, blank=True)
    formulation = models.CharField(max_length=1500)
    variant_a = models.CharField(max_length=150)
    variant_b = models.CharField(max_length=150)
    variant_c = models.CharField(max_length=150)
    variant_d = models.CharField(max_length=150)
    variant_e = models.CharField(max_length=150)
    answer_formulation = models.CharField(max_length=6000)
    right_variant = models.CharField(max_length=1)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    is_special = models.BooleanField(default=False)
    img = models.ImageField(upload_to='images', null=True, blank=True)
    value = models.IntegerField(default=50)
    chapter = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return """\\<b>#Problem N{}\\</b>{}\n{}\na. {}\nb. {}\nc. {}\nd. {}\ne. {}""".format(
            self.index, ("\nFrom chapter: #{}".format(self.chapter)
                         if self.chapter else ''), self.formulation,
            self.variant_a, self.variant_b, self.variant_c, self.variant_d,
            self.variant_e)

    def get_answer(self):
        return """\\<b>The right choice is {}\\</b>\n{}\n#Answer to {}\n""".format(
            self.right_variant, self.answer_formulation, self.index)

    def close(self, group):
        answers = Answer.objects.filter(
            problem=self,
            group_specific_participant_data__group=group,
            right=True,
            processed=False)
        for answer in answers:
            answer.process()
            answer.group_specific_participant_data.recalculate_roles()
        return self.get_leader_board(group, answers=answers)

    def get_leader_board(self, group, answers=None):
        answers = answers or Answer.objects.filter(
            problem=self,
            group_specific_participant_data__group=group,
            right=True,
            processed=False)
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

    class Meta:
        verbose_name = 'Problem'
        db_table = 'db_problem'


class GroupType(models.Model):
    """ Group Types """
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    @property
    def value(self):
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
    activeProblem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, blank=True, null=True)
    activeSubject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return '[{}] {}'.format(self.type.name, self.title or self.username)

    class Meta:
        verbose_name = 'Group'
        db_table = 'db_group'


class User(models.Model):
    """ User model """
    # Use id as telegram_id
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)

    @property
    def name(self):
        return self.first_name or self.username or self.last_name

    def __str__(self):
        return '{}'.format(self.first_name or self.username or self.last_name)

    class Meta:
        verbose_name = 'User'
        db_table = 'db_user'


class Bot(User):
    """ Bot model """
    token = models.CharField(max_length=50)
    offset = models.IntegerField(default=0)
    last_updated = models.DateTimeField(blank=True, null=True)

    @property
    def base_url(self):
        return 'https://api.telegram.org/bot{}/'.format(self.token)

    def update_information(self):
        url = self.base_url + 'getMe'
        resp = get_request(url)
        if resp:
            self.username = resp.get('username')
            self.first_name = resp.get('first_name')
            self.last_name = resp.get('last_name')
            self.save()

    def send_message(self,
                     group: 'text/id or group',
                     text,
                     *,
                     parse_mode='HTML',
                     reply_to_message_id=None):
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
            resp_c = get_request(url, payload=payload)
            logging.info(resp_c)
            resp.append(resp_c)
        return resp

    def send_image(self,
                   group: 'text/id or group',
                   image_file: io.BufferedReader,
                   *,
                   caption='',
                   reply_to_message_id=None):
        if not (isinstance(group, str) or isinstance(group, int)):
            group = group.telegram_id
        url = self.base_url + 'sendPhoto'
        payload = {
            'chat_id': group,
            'caption': caption,
            'reply_to_message_id': reply_to_message_id,
        }
        files = {'photo': image_file}
        resp = get_request(url, payload=payload, files=files)
        logging.info(resp)
        return resp

    def delete_message(self, group: str or Group, message_id: int or str):
        if not (isinstance(group, str) or isinstance(group, int)):
            group = group.telegram_id
        url = self.base_url + 'deleteMessage'
        payload = {'chat_id': group, 'message_id': message_id}
        resp = get_request(url, payload=payload)
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


class Role(models.Model):
    """ Role """
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    priority_level = models.IntegerField(default=1)
    from_stardard_kit = models.BooleanField(default=False)

    def __str__(self):
        return '[{}] {}'.format(self.priority_level, self.name)

    class Meta:
        verbose_name = 'Role'
        db_table = 'db_role'


class ScoreThreshold(models.Model):
    """ Score threshold """
    range_min = models.IntegerField()
    range_max = models.IntegerField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def __str__(self):
        return '{} [{}; {}]'.format(self.role.name, self.range_min,
                                    self.range_max)

    class Meta:
        verbose_name = 'Score Threshold'
        db_table = 'db_score_threshold'


class GroupSpecificParticipantData(models.Model):
    """ Group-specific participant data """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    joined = models.DateTimeField(blank=True, null=True)

    @property
    def percentage(self):
        if self.score >= 500:
            return round((1 - sum(
                answer.problem.value
                for answer in self.answer_set.filter(right=False)) / self.score
                          ) * 1000) / 10

    def recalculate_roles(self):
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

    def get_highest_role_binding(self):
        res = None
        for binding in self.participantgroupbinding_set.all():
            if not res or binding.role.priority_level > res.role.priority_level:
                res = binding
        return res

    def __str__(self):
        return '{}-{{{}}}->{}'.format(self.participant, self.score, self.group)

    class Meta:
        verbose_name = 'Group Specific Participant Data'
        db_table = 'db_group_specific_participant_data'


class ParticipantGroupBinding(models.Model):
    """ Participant-Group binding 
    - Same participant can have multiple bindings in the same group"""
    groupspecificparticipantdata = models.ForeignKey(
        GroupSpecificParticipantData, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def __str__(self):
        return '{}-{{{}}}->{}'.format(
            self.groupspecificparticipantdata.participant, self.role.name,
            self.groupspecificparticipantdata.group)

    class Meta:
        verbose_name = 'Participant-Group Binding'
        db_table = 'db_participant_group_binding'


class BotBinding(models.Model):
    """ Binding of a bot """
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        return '{}->{}'.format(self.bot, self.group)

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

    def process(self):
        if self.right and not self.processed:
            self.group_specific_participant_data.score += self.problem.value
            self.group_specific_participant_data.save()
            self.group_specific_participant_data.participant.sum_score += self.problem.value
            self.group_specific_participant_data.participant.save()
            self.processed = True
            self.save()

    class Meta:
        verbose_name = 'Answer'
        db_table = 'db_answer'


class SubjectGroupBinding(models.Model):
    """ Subject-Group binding """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    last_problem = models.ForeignKey(Problem, on_delete=models.CASCADE)

    def __str__(self):
        return '{}->{}'.format(self.subject, self.group)

    class Meta:
        verbose_name = 'Subject-Group Binding'
        db_table = 'db_subject_group_binding'
