"""
CLI Arguments
- HTML file path/replative_path
- Text to replace images
- image file names
"""

import sys
import os
import re


def replace_images_with_text(HTML_path, text, images):
    HTML = open(HTML_path, 'r').read()
    for img in images:
        # print(f"Processing {img}, changing to {text}")
        img, ext = os.path.splitext(img)
        if not ext:
            ext = '.jpg'
        HTML = re.sub(
            r'<img[^s]+src="[^/]+/' + img + ext + r'"\s+/>',
            text,
            HTML,
            flags=re.MULTILINE)
    # print(
    #     "Saving in ",
    #     os.path.abspath(os.path.dirname(HTML_path)) + '/' + os.path.splitext(
    #         os.path.basename(HTML_path))[0] + '_output' + '.html')
    # open(
    #     os.path.abspath(os.path.dirname(HTML_path)) + '/' + os.path.splitext(
    #         os.path.basename(HTML_path))[0] + '_output' + '.html',
    #     'w').write(HTML)
    open(HTML_path, 'w').write(HTML)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        replace_images_with_text(
            sys.argv[1] if sys.argv[1][0] in '~/' else
            os.getcwd() + '/' + sys.argv[1], sys.argv[2], sys.argv[3:])
    else:
        replace_images_with_text(
            '../local/PreTest-InternalMedicine/Medicine PreTest Self-Assessment and Review - 2015.html', '', ['Image_011.jpg, '])
