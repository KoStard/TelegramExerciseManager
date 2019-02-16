from django.contrib import admin
from main.universals import safe_getter
from main.models import *


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "value",
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "value",
        "discipline",
    )


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "index",
        "formulation",
        "right_variant",
        "subject",
        "chapter",
        "is_special",
        "img",
        "value",
    )


@admin.register(ParticipantDefinedProblem)
class ParticipantDefinedProblemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "problem_name",
        "participant",
        "formulation",
        "right_variant",
        "img",
        "value",
    )


@admin.register(GroupType)
class GroupTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "telegram_id",
        "username",
        "title",
        "type",
    )


@admin.register(ParticipantGroupPlayingModePrincipal)
class ParticipantGroupPlayingModePrincipalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "value",
    )


@admin.register(ParticipantGroupPlayingMode)
class ParticipantGroupPlayingModeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "value",
        "principal",
        "data",
    )


@admin.register(ParticipantGroup)
class ParticipantGroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "telegram_id",
        "username",
        "title",
        "type",
        "active_problem",
        "active_subject_group_binding",
        "playingMode",
    )

    def active_problem(current, self):
        return safe_getter(self, 'self.activeProblem.index')

    active_problem.admin_order_field = "activeProblem__index"

    def active_subject_group_binding(current, self):
        return safe_getter(self, 'self.activeSubjectGroupBinding')

    active_subject_group_binding.admin_order_field = "activeSubjectGroupBinding"


@admin.register(AdministratorPage)
class AdministratorPageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "telegram_id",
        "username",
        "title",
        "type",
        "participant_group",
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "first_name",
        "last_name",
    )


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "first_name",
        "last_name",
        "token",
        "offset",
        "last_updated",
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "first_name",
        "last_name",
        "sum_score",
    )


@admin.register(SuperAdmin)
class SuperAdminAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "value",
        "priority_level",
        "from_stardard_kit",
    )


@admin.register(ScoreThreshold)
class ScoreThresholdAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "role",
        "range_min",
        "range_max",
    )


@admin.register(GroupSpecificParticipantData)
class GroupSpecificParticipantDataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "participant",
        "participant_group",
        "score",
        "joined",
    )


@admin.register(ViolationType)
class ViolationTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "cost",
        "value",
    )


@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "groupspecificparticipantdata",
        "date",
        "type",
    )


@admin.register(ParticipantGroupBinding)
class ParticipantGroupBindingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "groupspecificparticipantdata",
        "role",
    )


@admin.register(BotBinding)
class BotBindingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bot",
        "participant_group",
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "Problem",
        "Answer",
        "right",
        "processed",
        "group_specific_participant_data",
        "date",
    )

    def Problem(current, self):
        return safe_getter(self, 'self.problem.index')

    Problem.admin_order_field = "problem__index"

    def Answer(current, self):
        return safe_getter(self,
                           'self.answer.upper() if self.answer else ' - '')

    Answer.admin_order_field = "answer__upper() if self__answer else '-'"


@admin.register(SubjectGroupBinding)
class SubjectGroupBindingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject",
        "participant_group",
        "Last_problem",
    )

    def Last_problem(current, self):
        return safe_getter(self, 'self.last_problem.index')

    Last_problem.admin_order_field = "last_problem__index"


@admin.register(TelegraphAccount)
class TelegraphAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "access_token",
        "auth_url",
    )


@admin.register(TelegraphPage)
class TelegraphPageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "path",
        "url",
        "account",
        "participant_group",
    )
