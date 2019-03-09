"""
Convert TXT from HTML_to_txt to json + has to be added #s before chapter names
Just give the file path
- check points after numbers

Have to manually replace \\n\\n to \\n in json
"""

import json
import sys
import re


def txt_to_json(path):
    res = []
    active_problem = None
    active_answer_problem_id = None
    problem_cursor = -1
    answer_cursor = -1
    mode = None
    current_chapter = None
    ind = 0
    data = open(path, 'r', encoding='utf-8').readlines()

    waiting_problems = []  # Questions ... and/to ...
    problem_formulation_buffer = {}
    problem_variants_buffer = {}
    waiting_answers = []  # Answers ...
    with_list = False

    for line in (l[:-1].replace('\u200c', '') for l in data):
        if 'A 19-year-old college student is being ' in line:
            print(line, waiting_problems, mode, active_problem)
        if line[0] == '#':
            # Handing chapter names
            current_chapter = line[1:]
            active_problem = None
        elif line[0] == '$':
            # Handing splitters
            active_problem = None
            if line[1:] == 'Questions':
                mode = 'q'
            elif line[1:] == 'Answers':
                mode = 'a'
            else:
                print(f"Invalid command {line}")
        elif line[0] == '^':
            active_problem = None
            need_question_split = re.match(r'\^Questions (\d+)\s(?:to|and)\s(\d+)', line)
            if need_question_split:
                waiting_problems = list(
                    range(int(need_question_split.group(1)) - 1, int(need_question_split.group(2))))
                problem_formulation_buffer = {}
                problem_variants_buffer = {}
                continue
            need_answer_split = re.match(
                r'\^Answers (\d+) (?:and|to) (\d+)\. The answers are((?:\s*\d+-\w[^\d.]+)+\d+-\w)\. ', line)
            if need_answer_split:
                waiting_answers = list(range(int(need_answer_split.group(1)) - 1, int(need_answer_split.group(2))))
                for right_variant_binding in need_answer_split.group(3).split(', '):
                    # print(right_variant_binding)
                    for f in re.finditer(r'(\d+)-(\w)', right_variant_binding):
                        # print(int(f.group(1)) - 1)
                        res[int(f.group(1)) - 1]['right_answer'] = f.group(2)
                for index in waiting_answers:
                    if index != waiting_answers[-1]:
                        res[index]['answer_formulation'] = 'The explanation will be posted with problem N{}'.format(
                            waiting_answers[-1] + 1)
                    else:
                        res[index]['answer_formulation'] += line[len(need_answer_split.group()):] + '\n'
                    answer_cursor += 1
                waiting_answers = waiting_answers[-1:]
                # answer_cursor = waiting_answers[-1]
                continue
        else:
            # Hadling regular lines
            if line == '!START_LIST!':
                if waiting_problems or waiting_answers:
                    with_list = True
                continue
            if line == '!END_LIST!':
                with_list = False
                continue
            if mode == 'q':
                mtch = re.match(r'(\d+)\.', line)
                if mtch:
                    if waiting_problems:
                        if not with_list:
                            waiting_problems = []
                        else:
                            for index in waiting_problems:
                                problem_variants_buffer[index] = problem_variants_buffer.get(index, []) + [
                                    line[len(mtch.group()) + 1:]]
                            #     res[index]['variants'].append(line[len(mtch.group()) + 1:])
                    if waiting_problems:
                        continue
                    if not active_problem or int(mtch.group(1)) > 5 or len(
                            active_problem['variants']) == 5:
                        # Handle new problem
                        problem_cursor += 1
                        res.append({
                            'index': problem_cursor,
                            'formulation': (problem_formulation_buffer[
                                                problem_cursor] + '\n' if problem_cursor in problem_formulation_buffer else '') + line[
                                                                                                                                  len(
                                                                                                                                      mtch.group()) + 1:],
                            'variants': problem_variants_buffer[
                                problem_cursor] if problem_cursor in problem_variants_buffer else [],
                            'chapter': current_chapter,
                            'images': [],
                            'answer_images': [],
                            'answer_formulation': '',
                            'predefined_variants_count': len(problem_variants_buffer[
                                                                 problem_cursor] if problem_cursor in problem_variants_buffer else [])
                        })
                        if problem_cursor in problem_formulation_buffer:
                            del problem_formulation_buffer[problem_cursor]
                        if problem_cursor in problem_variants_buffer:
                            del problem_variants_buffer[problem_cursor]
                        active_problem = res[-1]
                    else:
                        active_problem['variants'].append(line[len(mtch.group()) + 1:])
                else:
                    if active_problem:
                        if active_problem['variants'] and len(active_problem['variants']) > active_problem[
                            'predefined_variants_count']:
                            active_problem['variants'][-1] += ('\n' if line[0] != '\n' else '') + line
                        else:
                            active_problem['formulation'] += ('\n' if line[0] != '\n' else '') + line
                    elif waiting_problems:
                        for index in waiting_problems:
                            if with_list or problem_variants_buffer:
                                problem_variants_buffer[index][-1] += ('\n' if line[0] != '\n' else '') + line
                                # res[index]['variants'][-1] += ('\n' if line[0] != '\n' else '') + line
                            else:
                                if index in problem_formulation_buffer:
                                    problem_formulation_buffer[index] += ('\n' if problem_formulation_buffer[index][
                                                                                      -1] == '.' else ' ') + line
                                else:
                                    problem_formulation_buffer[index] = line
                                # res[index]['formulation'] += ('\n' if line[0] != '\n' else '') + line
            elif mode == 'a':
                mtch = re.match(r'(\d+)\. The answer is (\w)\. ', line)
                # print(mtch, waiting_answers)
                if mtch:
                    waiting_answers = []
                    answer_cursor += 1
                    res[answer_cursor]['right_answer'] = mtch.group(2)
                    res[answer_cursor]['answer_formulation'] = line[len(mtch.group()):]
                else:
                    if waiting_answers:
                        for index in waiting_answers:
                            res[index]['answer_formulation'] += ('\n' if line[0] != '\n' else '') + line
                    else:
                        res[answer_cursor]['answer_formulation'] += ('\n' if line[0] != '\n' else '') + line
                    # print("Didn't match", line[:70])

    cmp = re.compile(r'[\n]*@(Image_[^@]+)@')
    for problem in res:
        for m in reversed(list(cmp.finditer(problem['formulation']))):
            problem['formulation'] = problem['formulation'][:m.start()] + problem['formulation'][m.end():]
            image = m.group(1)[:]
            problem['images'].append(
                'media/Medicine PreTest Self-Assessment and Review - 2015/' + image)

        if problem['answer_formulation']:
            for m in reversed(list(cmp.finditer(problem['answer_formulation']))):
                problem['answer_formulation'] = problem['answer_formulation'][:m.start()] + problem[
                                                                                                'answer_formulation'][
                                                                                            m.end():]
                image = m.group(1)[:]
                problem['answer_images'].append(
                    'media/Medicine PreTest Self-Assessment and Review - 2015/' + image)
        else:
            print("No answer formulation", problem)
            pass

        for i in range(len(problem['variants'])):
            for m in reversed(list(cmp.finditer(problem['variants'][i]))):
                problem['variants'][i] = problem['variants'][i][:m.start()] + problem['variants'][i][
                                                                              m.end():]
                image = m.group(1)[:]
                problem['images'].append(
                    'media/Medicine PreTest Self-Assessment and Review - 2015/' + image)
        if 'right_answer' not in problem:
            print("WARNING", problem['index'])
    # if cmp.search(problem['formulation']):
    #     if len(cmp.findall(problem['formulation'])) > 1:
    #         print("Problem", problem)
    # if cmp.search(problem['answer_formulation']):
    #     if len(cmp.findall(problem['answer_formulation'])) > 1:
    #         print("Answer", problem)
    open(path[:-3] + 'json', 'w', encoding='utf-8').write(json.dumps(res))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        txt_to_json(sys.argv[1])
    else:
        txt_to_json('../local/PreTest-InternalMedicine/Medicine PreTest Self-Assessment and Review - 2015.txt')
