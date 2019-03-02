import sys
from bs4 import BeautifulSoup
import re
res = []


def handle_question(question):

    parts = [el for el in question.children if hasattr(el, 'tag')]
    if len(parts) != 2:
        print("HERE")
        pass
    print(len(parts))


def handle_questions(cont):
    questions = [el for el in cont.children if hasattr(el, 'tag')]
    print(len(questions), 'questions')
    for question in questions:
        handle_question(question)


def process_book_html_to_json(path):
    global res
    res = []
    soup = BeautifulSoup(open(path), 'html.parser')
    active_group = None
    active_chapter = None
    for cont in soup.children:
        if not hasattr(cont, 'tag') or not cont.text:
            continue
        if not active_chapter:
            active_chapter = re.sub('\s{2,}', ' ', ' '.join(
                cont.text.split('\n')[-2:]))[:-1]
        if re.match("Questions", cont.text):
            active_group = 'q'
        elif active_group == 'q':
            handle_questions(cont)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            process_book_html_to_json(path)
    else:
        process_book_html_to_json(
            'main/local/ConvertingProblems/PreTest-Physiology/(PreTest Basic Science) Patricia Metting - Physiology PreTest Self-Assessment and Review-McGraw-Hill Medical (2013)_output.html'
        )
