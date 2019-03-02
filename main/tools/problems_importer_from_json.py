"""
Just give json filepath to import models from there
"""

from django.core.files import File
import django
import sys
import os
import json

sys.path.append(
    "E:/Programming/Python/Django/Telegram Problem Controller/TelegramProblemGenerator/"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "TelegramProblemGenerator.settings")

django.setup()

from main.models import *


def load_problems(filepath):
    problems = json.loads(open(filepath, 'r', encoding='utf-8').read())
    for problem in problems:
        p = Problem(
            index=problem['index']+1,
            formulation=problem['formulation'],
            variant_a=problem['variants'][0] if 0 < len(problem['variants']) else "[[EMPTY]]",
            variant_b=problem['variants'][1] if 1 < len(problem['variants']) else "[[EMPTY]]",
            variant_c=problem['variants'][2] if 2 < len(problem['variants']) else "[[EMPTY]]",
            variant_d=problem['variants'][3] if 3 < len(problem['variants']) else "[[EMPTY]]",
            variant_e=problem['variants'][4] if 4 < len(problem['variants']) else "[[EMPTY]]",
            answer_formulation=problem['answer_formulation'],
            right_variant=problem['right_answer'],
            subject=Subject.objects.get(value='pretest_physiology_2013'),
            chapter=problem['chapter'],
        )
        p.save()
        for img in problem['images']:
            image = ProblemImage(
                problem=p,
                image=File(open(img)),
                for_answer=False
            )
            image.save()
        for img in problem['answer_images']:
            image = ProblemImage(
                problem=p,
                image=File(open(img)),
                for_answer=True
            )
            image.save()
    print("Done")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        load_problems(sys.argv[1])
    else:
        load_problems("../local/ConvertingProblems/PreTest-Physiology/Text+Image-success-1.json")

from main.models import Subject, ProblemImage
subject = Subject.objects.get(value='pretest_physiology_2013')
for problem in data:
    p = subject.problem_set.get(index=problem['index']+1)
    for img in problem['images']:
        image = ProblemImage(
            problem=p,
            image=File(open(img, 'rb')),
            for_answer=False
        )
        image.save()
    for img in problem['answer_images']:
        image = ProblemImage(
            problem=p,
            image=File(open(img, 'rb')),
            for_answer=True
        )
        image.save()