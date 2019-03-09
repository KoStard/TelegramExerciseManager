"""
Just give json filepath to import models from there
"""

from django.core.files import File
import django
import sys
import os
import json
from pathlib import Path

sys.path.append(
    "E:/Programming/Python/Django/Telegram Problem Controller/TelegramProblemGenerator/"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "TelegramProblemGenerator.settings")

django.setup()

from main.models import *


def load_problems(filepath):
    problems = json.loads(open(filepath, 'r', encoding='utf-8').read())
    base = Path(__file__).parent.parent.parent
    for problem in problems:
        if max([len(v) for v in problem['variants']] or [0]) > 250:
            print(problem['index'])
        p = Problem(
            index=problem['index']+1,
            formulation=problem['formulation'],
            variants=problem['variants'] or [],
            answer_formulation=problem['answer_formulation'],
            right_variant=problem['right_answer'],
            subject=Subject.objects.get(value='pretest_internalmedicine'),
            chapter=problem['chapter'],
        )
        p.save()
        for img in problem['images']:
            image = ProblemImage(
                problem=p,
                image=File(str(base / img)),
                for_answer=False
            )
            image.save()
        for img in problem['answer_images']:
            image = ProblemImage(
                problem=p,
                image=File(str(base / img)),
                for_answer=True
            )
            image.save()
    print("Done")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        load_problems(sys.argv[1])
    else:
        load_problems("../local/PreTest-InternalMedicine/Medicine PreTest Self-Assessment and Review - 2015.json")
