from django.contrib import admin
from main.models import *


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "value",
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "value",
        "discipline",
    )


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = (
        "index",
        "formulation",
        "right_variant",
        "subject",
        "chapter",
        "is_special",
        "img",
        "value",
    )


@admin.register(GroupType)
class GroupTypeAdmin(admin.ModelAdmin):
    list_display = ("name", )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "title",
        "type",
    )


@admin.register(ParticipantGroup)
class ParticipantGroupAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "title",
        "type",
        "active_problem",
        "active_subject_group_binding",
    )

    def active_problem(current, self):
        return self.activeProblem.index

    active_problem.admin_order_field = "activeProblem__index"

    def active_subject_group_binding(current, self):
        return self.activeSubjectGroupBinding

    active_subject_group_binding.admin_order_field = "activeSubjectGroupBinding"


@admin.register(AdministratorPage)
class AdministratorPageAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "title",
        "type",
        "group_ptr",
        "participant_group",
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
    )


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "user_ptr",
        "token",
        "offset",
        "last_updated",
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "user_ptr",
        "sum_score",
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "value",
        "priority_level",
        "from_stardard_kit",
    )


@admin.register(ScoreThreshold)
class ScoreThresholdAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "range_min",
        "range_max",
    )


@admin.register(GroupSpecificParticipantData)
class GroupSpecificParticipantDataAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "participant_group",
        "score",
        "joined",
    )


@admin.register(ParticipantGroupBinding)
class ParticipantGroupBindingAdmin(admin.ModelAdmin):
    list_display = (
        "groupspecificparticipantdata",
        "role",
    )


@admin.register(BotBinding)
class BotBindingAdmin(admin.ModelAdmin):
    list_display = (
        "bot",
        "participant_group",
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        "Problem",
        "Answer",
        "right",
        "processed",
        "group_specific_participant_data",
        "date",
    )

    def Problem(current, self):
        return self.problem.index

    Problem.admin_order_field = "problem__index"

    def Answer(current, self):
        return self.answer.upper()

    Answer.admin_order_field = "answer__upper()"


@admin.register(SubjectGroupBinding)
class SubjectGroupBindingAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "participant_group",
        "Last_problem",
    )

    def Last_problem(current, self):
        return self.last_problem.index

    Last_problem.admin_order_field = "last_problem__index"


@admin.register(TelegraphAccount)
class TelegraphAccountAdmin(admin.ModelAdmin):
    list_display = (
        "access_token",
        "auth_url",
    )


@admin.register(TelegraphPage)
class TelegraphPageAdmin(admin.ModelAdmin):
    list_display = (
        "path",
        "url",
        "account",
        "participant_group",
    )


@admin.register(SuperAdmin)
class SuperAdminAdmin(admin.ModelAdmin):
    list_display = ("user", )
