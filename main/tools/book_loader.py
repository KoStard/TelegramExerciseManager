import sys
from bs4 import BeautifulSoup
import re
import os
from unicodedata import normalize

problems = []

char_map = {
    'вЂ“': '-',
    '\n': ''
}

current_problem = 0
current_answer = 0
active_group = None
active_chapter = None


def standardize_text(text: str) -> str:
    output = ''
    for key in char_map:
        if len(key) > 1:
            text = text.replace(key, char_map[key])
    for c in text:
        if c in char_map:
            output += char_map[c]
        elif c != ' ' or (output and output[-1] != ' '):
            output += c
    return output


def handle_question(question):
    global current_problem, problems
    current_problem += 1
    parts = [el for el in question.children if hasattr(el, 'tag')]
    formulation = ''
    variants = []
    images = []
    for part in parts:
        if 's17' in part.attrs.get('class', []):
            handle_splitter_tag(part)
            return
        if part.name == 'p':
            if formulation and formulation[-1] in '.:':
                formulation += '\n' + part.text
            else:
                formulation += part.text
            img = part.find('img')
            if img:
                images.append(img.attrs['src'])
        elif part.name == 'ol':
            variants_temp = [v for v in part.children if hasattr(v, 'tag')]
            if len(variants_temp) == 5:
                variants = [standardize_text(v.text) for v in variants_temp]
            else:
                print(f"Invalid problem {current_problem}")
    formulation = standardize_text(formulation)
    problems.append({
        'formulation': formulation,
        'variants': variants
    })


def handle_questions(cont):
    questions = [el for el in cont.children if hasattr(el, 'tag')]
    print(len(questions), 'questions')
    for question in questions:
        handle_question(question)


def handle_answer(answer_elem):
    pass


def handle_answers(cont):
    pass


def handle_splitter_tag(tag):
    text = normalize('NFC', tag.text)
    if text == 'Questions‌':
        print("Questions‌")
    elif text == 'Answers‌':
        print("Answers‌")
    else:
        print("Invalid tag")


def process_book_html_to_json(path):
    global problems, active_chapter, active_group
    problems = []
    soup = BeautifulSoup(open(path), 'html.parser')
    for cont in soup.children:
        if not hasattr(cont, 'tag') or not cont.text:
            continue
        if not active_chapter:
            active_chapter = re.sub('\s{2,}', ' ', ' '.join(
                cont.text.split('\n')[-2:]))[:-1]
        # print(cont.text)
        if 's17' in cont.attrs.get('class', []):
            handle_splitter_tag(cont)
        elif active_group == 'q':
            handle_questions(cont)
        elif active_group == 'a':
            handle_answers(cont)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            process_book_html_to_json(path)
    else:
        process_book_html_to_json(
            os.path.abspath(
                os.getcwd() + '/../local/ConvertingProblems/PreTest-Physiology/(PreTest Basic Science) Patricia Metting - Physiology PreTest Self-Assessment and Review-McGraw-Hill Medical (2013)_output.html')
        )
