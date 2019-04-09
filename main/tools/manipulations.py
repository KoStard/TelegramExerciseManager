from main.models import GroupSpecificParticipantData, Answer


def simulate_answering(pg, first_name, answer, last_name=0, id=0):
    part_args = {'participant_group': pg, 'participant__first_name': first_name}
    if last_name != 0:
        part_args['participant__last_name'] = last_name
    if id != 0:
        part_args['participant__id'] = id
    part = GroupSpecificParticipantData.objects.get(**part_args)
    args = {
        'problem': pg.activeProblem,
        'answer': answer,
        'right': answer.upper() == pg.activeProblem.right_variant.upper(),
        'group_specific_participant_data': part
    }
    return Answer.objects.create(**args)


def inactivate(answers):
    for answer in answers:
        answer.processed = False
        answer.save()
        print(f"Inactivated {answer.group_specific_participant_data.participant.first_name}")


def make_right(answers):
    for answer in answers:
        answer.right = True
        answer.save()
        print(f"Made right {answer.group_specific_participant_data.participant.first_name}")


def get_answers(pg):
    return sorted(Answer.objects.filter(group_specific_participant_data__participant_group=pg, problem=pg.activeProblem,
                                        processed=False), key=lambda answer: answer.id)


def get_answer_names(pg):
    return [answer.group_specific_participant_data.participant.first_name for answer in get_answers(pg)]
