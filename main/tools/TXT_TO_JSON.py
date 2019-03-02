"""
Convert TXT from HTML_to_txt to json + has to be added #s before chapter names
Just give the file path
- check points after numbers
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

    problem_indexes = []
    answer_indexes = []

    for line in (l[:-1].replace('\u200c', '') for l in data):
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
        else:
            # Hadling regular lines
            if mode == 'q':
                mtch = re.match(r'(\d+)\.', line)
                if mtch:
                    if not active_problem or int(mtch.group(1)) > 5 or len(
                            active_problem['variants']) == 5:
                        # Handle new problem
                        problem_cursor += 1
                        problem_indexes.append(mtch.group(1))
                        res.append({
                            'index': problem_cursor,
                            'formulation': line[len(mtch.group()) + 1:],
                            'variants': [],
                            'chapter': current_chapter,
                            'images': [],
                            'answer_images': []
                        })
                        active_problem = res[-1]
                    else:
                        active_problem['variants'].append(line[len(mtch.group()) + 1:])
                else:
                    if not active_problem:
                        print("Something gone wrong, no active problem")
                        break
                    elif active_problem['variants']:
                        active_problem['variants'][-1] += '\n' + line
                    else:
                        active_problem['formulation'] += '\n' + line
            elif mode == 'a':
                mtch = re.match(r'(\d+)\. The answer is (\w)\. ', line)
                if mtch:
                    answer_cursor += 1
                    answer_indexes.append(mtch.group(1))
                    res[answer_cursor]['right_answer'] = mtch.group(2)
                    res[answer_cursor]['answer_formulation'] = line[len(mtch.group()):]
                else:
                    res[answer_cursor]['answer_formulation'] += '\n' + line
                    # print("Didn't match", line[:70])
    cmp = re.compile(r'[\n]*@(Image_[^@]+)@')
    for problem in res:
        for m in cmp.finditer(problem['formulation']):
            problem['formulation'] = problem['formulation'][:m.start()] + problem['formulation'][m.end():]
            image = m.group(1)[:]
            problem['images'].append('main/local/ConvertingProblems/PreTest-Physiology/Images/'+image)

        for m in cmp.finditer(problem['answer_formulation']):
            problem['answer_formulation'] = problem['answer_formulation'][:m.start()] + problem['answer_formulation'][m.end():]
            image = m.group(1)[:]
            problem['answer_images'].append('main/local/ConvertingProblems/PreTest-Physiology/Images/'+image)

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
        txt_to_json('../local/ConvertingProblems/PreTest-Physiology/Text+Image-success-1.txt')
