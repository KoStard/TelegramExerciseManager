from django.contrib import admin
from main.models import *


class DisciplineAdmin(admin.ModelAdmin):
    pass


class SubjectAdmin(admin.ModelAdmin):
    pass


class ProblemAdmin(admin.ModelAdmin):
    pass


class GroupTypeAdmin(admin.ModelAdmin):
    pass


class GroupAdmin(admin.ModelAdmin):
    pass


class UserAdmin(admin.ModelAdmin):
    pass


class BotAdmin(admin.ModelAdmin):
    pass


class ParticipantAdmin(admin.ModelAdmin):
    pass


class GroupSpecificParticipantDataAdmin(admin.ModelAdmin):
    pass


class RoleAdmin(admin.ModelAdmin):
    pass


class ParticipantGroupBindingAdmin(admin.ModelAdmin):
    pass


class BotBindingAdmin(admin.ModelAdmin):
    pass


class AnswerAdmin(admin.ModelAdmin):
    pass


class SubjectGroupBindingAdmin(admin.ModelAdmin):
    pass


admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Problem, ProblemAdmin)
admin.site.register(GroupType, GroupTypeAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Bot, BotAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(GroupSpecificParticipantData, GroupSpecificParticipantDataAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(ParticipantGroupBinding, ParticipantGroupBindingAdmin)
admin.site.register(BotBinding, BotBindingAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(SubjectGroupBinding, SubjectGroupBindingAdmin)
