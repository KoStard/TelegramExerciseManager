"""
When running from cli, give picture path and folder path as arguments
"""
from PIL import Image
from PIL import ImageChops
import sys
import os
import math
import operator
from functools import reduce

remove_duplicates = False


def equal(im1, im2):
    try:
        return ImageChops.difference(im1, im2).getbbox() is None
    except ValueError as e:
        # print(e)
        return None


def histCompare(im1, im2):
    h1 = im1.histogram()
    h2 = im2.histogram()

    rms = math.sqrt(
        reduce(operator.add, map(lambda a, b: (a - b)**2, h1, h2)) / len(h1))
    return rms


def find_similar_pictures(path, folder_path):
    res = []
    gen_img = Image.open(path)
    for current_image_name in os.listdir(folder_path):
        if current_image_name == os.path.basename(path):
            res.append(current_image_name)
            continue
        if current_image_name[0] == '.':
            continue
        curr_img = Image.open(folder_path + current_image_name)
        # print(f"Checking {current_image_name}")
        if equal(gen_img, curr_img):
            # print("Equal")
            if remove_duplicates:
                os.remove(folder_path + current_image_name)
            else:
                res.append(current_image_name)
        elif histCompare(gen_img, curr_img) < 5:
            # print("New equal")
            res.append(current_image_name)
        else:
            # print("Not equal")
            pass
    return res


if __name__ == '__main__':
    print(
        *find_similar_pictures(
            sys.argv[1] if sys.argv[1][0] in '~/' else os.getcwd() + '/' +
            sys.argv[1], sys.argv[2] if sys.argv[2][0] in '~/' else
            os.getcwd() + '/' + (sys.argv[2] if sys.argv[2] != '.' else '')),
        sep=' ')
