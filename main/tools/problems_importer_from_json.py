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
    subject = Subject.objects.get(value='pretest_internalmedicine')
    for problem in problems:
        # p = Problem(
        #     index=problem['index']+1,
        #     formulation=problem['formulation'],
        #     variants=problem['variants'] or [],
        #     answer_formulation=problem['answer_formulation'],
        #     right_variant=problem['right_answer'],
        #     subject=Subject.objects.get(value='pretest_internalmedicine'),
        #     chapter=problem['chapter'],
        # )
        # p.save()
        p = subject.problem_set.get(index=problem['index']+1)
        index = 0
        images = sorted(list(p.problemimage_set.filter(for_answer=False)), key=lambda img: img.id)
        for img in problem['images'][::-1]:
            # image = ProblemImage(
            #     problem=p,
            #     image=File(open(str(base / img))),
            #     for_answer=False
            # )
            image = images[index]
            image.image = File(open('../../' + img, 'rb'))
            image.image.name = img
            index += 1
            if p.index == 131:
                print(image.id, img)
            # open('../../'+img, 'rb')
            image.save()
        index = 0
        images = sorted(list(p.problemimage_set.filter(for_answer=True)), key=lambda img: img.id)
        for img in problem['answer_images'][::-1]:
            # image = ProblemImage(
            #     problem=p,
            #     image=File(open(str(base / img))),
            #     for_answer=True
            # )

            image = images[index]
            image.image = File(open('../../' + img, 'rb'))
            image.image.name = img
            index += 1
            if p.index == 131:
                print(image.id, img)
            # open('../../'+img, 'rb')
            image.save()
    print("Done")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        load_problems(sys.argv[1])
    else:
        load_problems("../local/PreTest-InternalMedicine/Medicine PreTest Self-Assessment and Review - 2015.json")



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
    subject = Subject.objects.get(value='pretest_internalmedicine')
    for problem in problems:
        p = Problem(
            index=problem['index']+1,
            formulation=problem['formulation'],
            variants=problem['variants'] or [],
            answer_formulation=problem['answer_formulation'],
            right_variant=problem['right_answer'],
            subject=subject,
            chapter=problem['chapter'],
        )
        p.save()
        for img in problem['images'][::-1]:
            image = ProblemImage(
                problem=p,
                image=File(open(str(base / img))),
                for_answer=False
            )
            image.save()
        for img in problem['answer_images'][::-1]:
            image = ProblemImage(
                problem=p,
                image=File(open(str(base / img))),
                for_answer=True
            )
            image.save()
    print("Done")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        load_problems(sys.argv[1])
    else:
        load_problems("../local/PreTest-InternalMedicine/Medicine PreTest Self-Assessment and Review - 2015.json")
"""