import copy
import os
from typing import List, Union, Any, Tuple
import argparse

import fitz  # install with 'pip install pymupdf'


def get_markups(annot: fitz.Annot, intersect_threshold: float = 0.9) -> Tuple:
    vertices = annot.vertices
    if not vertices:
        vertices = [(annot.rect.x0, annot.rect.y0), (annot.rect.x1, annot.rect.y0), (annot.rect.x0, annot.rect.y1), (annot.rect.x1, annot.rect.y1)]
    page = annot.parent
    rawdict = page.get_text('rawdict')
    words = ''
    loci = [0, 0.0, -1, 0, -1]

    if len(vertices) == 4:
        anno_rect = fitz.Quad(vertices[0:4]).rect
        line_idx = 0
        for block in rawdict['blocks']:
            if block['type'] == 0:
                for line in block['lines']:
                    char_idx = 0
                    line_words = ''
                    loci[0] = line_idx
                    loci[2] = -1
                    if fitz.Rect(line['bbox']).y0 <= (anno_rect.y0 + anno_rect.y1) / 2 <= fitz.Rect(line['bbox']).y1:
                        rect = copy.deepcopy(anno_rect)
                        rect.include_point(fitz.Point(anno_rect.x0, fitz.Rect(line['bbox']).y0))
                        rect.include_point(fitz.Point(anno_rect.x0, fitz.Rect(line['bbox']).y1))
                        for span in line['spans']:
                            for char in span['chars']:
                                line_words += char['c']
                                if char['bbox'] in rect or fitz.Rect(char['bbox']).intersect(rect).get_area() >= fitz.Rect(char['bbox']).get_area() * intersect_threshold:
                                    if loci[2] == -1:
                                        loci[1] = char['bbox'][0]
                                        loci[2] = char_idx
                                    loci[3] = line_idx
                                    loci[4] = char_idx + 1
                                char_idx += 1
                    if loci[2] != -1:
                        words = line_words[loci[2]:loci[4]]
                        break
                    line_idx += 1
            else:
                line_idx += 1
            if loci[2] != -1:
                break
    else:
        anno_rect = fitz.Quad(vertices[0:4]).rect
        line_idx = 0
        for block in rawdict['blocks']:
            if block['type'] == 0:
                for line in block['lines']:
                    char_idx = 0
                    loci[0] = line_idx
                    if fitz.Rect(line['bbox']).y0 <= (anno_rect.y0 + anno_rect.y1) / 2 <= fitz.Rect(line['bbox']).y1:
                        rect = copy.deepcopy(anno_rect)
                        rect.include_point(fitz.Point(anno_rect.x0, fitz.Rect(line['bbox']).y0))
                        rect.include_point(fitz.Point(anno_rect.x0, fitz.Rect(line['bbox']).y1))
                        for span in line['spans']:
                            for char in span['chars']:
                                if char['bbox'] in rect or fitz.Rect(char['bbox']).intersect(
                                        rect).get_area() >= fitz.Rect(char['bbox']).get_area() * intersect_threshold:
                                    if loci[2] == -1:
                                        loci[1] = char['bbox'][0]
                                        loci[2] = char_idx
                                        break
                                char_idx += 1
                    if loci[2] != -1:
                        break
                    line_idx += 1
            else:
                line_idx += 1
            if loci[2] != -1:
                break

        anno_rect = fitz.Quad(vertices[-4:]).rect
        line_idx = 0
        for block in rawdict['blocks']:
            if block['type'] == 0:
                for line in block['lines']:
                    char_idx = 0
                    loci[3] = line_idx
                    if fitz.Rect(line['bbox']).y0 <= (anno_rect.y0 + anno_rect.y1) / 2 <= fitz.Rect(line['bbox']).y1:
                        rect = copy.deepcopy(anno_rect)
                        rect.include_point(fitz.Point(anno_rect.x0, fitz.Rect(line['bbox']).y0))
                        rect.include_point(fitz.Point(anno_rect.x0, fitz.Rect(line['bbox']).y1))
                        for span in line['spans']:
                            for char in span['chars']:
                                if char['bbox'] in rect or fitz.Rect(char['bbox']).intersect(
                                        rect).get_area() >= fitz.Rect(char['bbox']).get_area() * intersect_threshold:
                                    loci[4] = char_idx + 1
                                char_idx += 1
                    if loci[4] != -1:
                        break
                    line_idx += 1
            else:
                line_idx += 1
            if loci[4] != -1:
                break

        line_idx = 0
        for block in rawdict['blocks']:
            if block['type'] == 0:
                for line in block['lines']:
                    char_idx = 0
                    if line_idx == loci[0]:
                        for span in line['spans']:
                            for char in span['chars']:
                                if char_idx >= loci[2]:
                                    words += char['c']
                                char_idx += 1
                        if line['spans'][-1]['chars'][-1]['c'].encode().isalpha() or line['spans'][-1]['chars'][-1]['c'].isdigit():
                            words += ' '
                    elif loci[0] <= line_idx <= loci[3]:
                        for span in line['spans']:
                            for char in span['chars']:
                                words += char['c']
                        if line['spans'][-1]['chars'][-1]['c'].encode().isalpha() or line['spans'][-1]['chars'][-1]['c'].isdigit():
                            words += ' '
                    elif line_idx == loci[3]:
                        for span in line['spans']:
                            for char in span['chars']:
                                if char_idx < loci[4]:
                                    words += char['c']
                    line_idx += 1
            else:
                line_idx += 1

    return words.replace('*', '\\*'), annot.type[0], loci, annot.rect, annot.info['content'].replace('*', '\\*')


def process_markups(markups: List, page: fitz.Page) -> List:

    markups = [markup for markup in markups if markup[0]]

    if not markups:
        return []

    line_ends = []

    rawdict = page.get_text('rawdict')
    for block in rawdict['blocks']:
        if block['type'] == 0:
            for line in block['lines']:
                line_end = 0
                for span in line['spans']:
                    line_end += len(span['chars'])
                if line['spans'][-1]['chars'][-1]['c'].encode().isalpha() or line['spans'][-1]['chars'][-1]['c'].isdigit():
                    line_end += 1
                line_ends.append(line_end)
        else:
            line_ends.append(0)

    terminals = []
    for i in range(len(markups)):
        markup = markups[i]
        start = markup[2][0], markup[2][2], i, True
        end = markup[2][3], markup[2][4], i, False
        terminals.append(start)
        terminals.append(end)

    terminals.sort(key=(lambda x: [x[0], x[1]]))

    def get_priority(markup_type: int) -> int:
        if markup_type == fitz.PDF_ANNOT_STRIKE_OUT:
            p = 1
        elif markup_type == fitz.PDF_ANNOT_HIGHLIGHT:
            p = 2
        else:
            p = 3
        return p

    def get_char_diff(i_temp: int) -> int:
        line_diff = terminals[i_temp + 1][0] - terminals[i_temp][0]
        if line_diff:
            cd = terminals[i_temp + 1][1] - terminals[i_temp][1]
            for ld in range(line_diff):
                cd += line_ends[terminals[i_temp][0] + ld]
        else:
            cd = terminals[i_temp + 1][1] - terminals[i_temp][1]
        return cd

    def get_words_from_span() -> str:
        words = ''
        all_markups = []
        idx = len(spans) - 1
        while idx >= 0:
            span = spans[idx]
            markup = markups[span[0]]
            word = markup[0][span[1]:span[2]]
            if markup[1] == fitz.PDF_ANNOT_UNDERLINE:
                if span[0] not in all_markups:
                    if markup[4]:
                        word = word.rstrip() + " (" + markup[4] + ") "
                        words = word + words.lstrip()
                    else:
                        words = word + words
                    all_markups.append(span[0])
                else:
                    words = word + words
            elif markup[1] == fitz.PDF_ANNOT_HIGHLIGHT:
                if span[0] not in all_markups:
                    if markup[4]:
                        if word == '' or word[0] == ' ':
                            word = " **" + word.lstrip()
                        else:
                            word = "**" + word
                        if word == '' or word[-1] == ' ':
                            word = word.rstrip() + " (" + markup[4] + ")** "
                        else:
                            word = word.rstrip() + " (" + markup[4] + ")**"
                        words = word + words.lstrip()
                    else:
                        if word == '' or word[0] == ' ':
                            word = " **" + word.lstrip()
                        else:
                            word = "**" + word
                        if word == '' or word[-1] == ' ':
                            word = word.rstrip() + "** "
                        else:
                            word = word + "**"
                        words = word + words
                    all_markups.append(span[0])
                else:
                    if word == '' or word[0] == ' ':
                        word = " **" + word.lstrip()
                    else:
                        word = "**" + word
                    if word == '' or word[-1] == ' ':
                        word = word.rstrip() + "** "
                    else:
                        word = word + "**"
                    words = word + words
            idx -= 1
        words.strip()
        return words

    def save_markup():
        markup_words = get_words_from_span()
        rect = fitz.Rect()
        for span in spans:
            rect.include_rect(markups[span[0]][3])
        if markup_words:
            new_markups.append((markup_words, fitz.PDF_ANNOT_UNDERLINE,
                                [markups[spans[0][0]][2][0], markups[spans[0][0]][2][1]], rect))

    new_markups = []

    status_now = []
    status_last = False
    status_hold = False

    for i in range(len(terminals) - 1):
        terminal = terminals[i]

        if not status_hold:
            if status_now:
                status_last = True
            else:
                status_last = False

        if terminal[3]:
            status_now.append([get_priority(markups[terminal[2]][1]), terminal[2], 0])
            if status_now:
                status_now.sort(key=(lambda x: x[0]))
        else:
            for s in status_now:
                if s[1] == terminal[2]:
                    status_now.remove(s)
                    break

        if terminal[0] == terminals[i + 1][0] and terminal[1] == terminals[i + 1][1]:
            status_hold = True
            continue

        if status_now and not status_last:  # Span starts
            status_hold = False
            spans = []
        elif not status_now and status_last:  # Span ends
            status_hold = False
            save_markup()

        if status_now:
            char_diff = get_char_diff(i)
            spans.append([status_now[0][1], status_now[0][2], status_now[0][2] + char_diff])
            for s in status_now:
                s[2] += char_diff

    save_markup()

    return new_markups


def get_texts(annot: fitz.Annot, num_free_text: int) -> Tuple:
    page = annot.parent
    annot_rect = annot.rect
    blocks = page.get_text('blocks')
    rawdict = page.get_text('rawdict')
    point = fitz.Point((annot_rect.x0 + annot_rect.x1)/2, annot_rect.y0)
    min_distance = page.rect.width + page.rect.height
    distance = 0.0
    closest_block = 0

    line_idx = 0
    for i in range(len(rawdict['blocks']) - num_free_text):
        block = rawdict['blocks'][i]
        if block['type'] == 0:
            for line in block['lines']:
                distance = point.distance_to(line['bbox'][0:4])
                if distance < min_distance:
                    min_distance = distance
                    closest_block = line_idx
                line_idx += 1
        else:
            line_idx += 1

    return annot.info['content'].replace('*', '\\*'), annot.type[0], [closest_block, 10000 + point.x + point.y], annot_rect, ''


def get_image_rect(annot: fitz.Annot, image_min=0.5) -> fitz.Rect:
    page = annot.parent
    page_rect = page.rect
    annot_rect = annot.rect
    min_width = page_rect.x1 * image_min
    if image_min <= 0 or annot_rect.x1 - annot_rect.x0 >= min_width:
        return annot_rect
    if image_min >= 1:
        return fitz.Rect(page_rect.x0, annot_rect.y0, page_rect.x1, annot_rect.y1)
    x_middle = (annot_rect.x0 + annot_rect.x1) / 2
    x0 = x_middle - min_width / 2
    x1 = x_middle + min_width / 2
    if x0 < 0:
        x0 = 0
        x1 = min_width
    elif x1 > page_rect.x1:
        x1 = page_rect.x1
        x0 = page_rect.x1 - min_width
    return fitz.Rect(x0, annot_rect.y0, x1, annot_rect.y1)


def get_squares(annot: fitz.Annot, num_free_text: int, intersect_threshold: float = 0.9, dpi: float = 300,
                image_min: float = 0.5) -> Tuple:
    page = annot.parent
    rect = annot.rect
    point = fitz.Point((rect.x0 + rect.x1)/2, rect.y0)
    rawdict = page.get_text('rawdict')
    words = ''
    min_distance = page.rect.width + page.rect.height
    distance = 0.0
    closest_line = 0
    line_idx = 0

    for i in range(len(rawdict['blocks']) - num_free_text):
        block = rawdict['blocks'][i]
        if block['type'] == 0:
            for line in block['lines']:
                distance = point.distance_to(line['bbox'])
                if distance < min_distance:
                    min_distance = distance
                    closest_line = line_idx
                for span in line['spans']:
                    for char in span['chars']:
                        if char['bbox'] in rect or fitz.Rect(char['bbox']).intersect(rect).get_area() >= \
                                fitz.Rect(char['bbox']).get_area() * intersect_threshold:
                            words += char['c']
                line_idx += 1
        else:
            line_idx += 1

    image_rect = get_image_rect(annot, image_min)

    return page.get_pixmap(clip=image_rect, dpi=dpi), annot.type[0], [closest_line,
                                                                      10000 + point.x + point.y], rect, words.replace('*', '\\*')


def get_annots(page: fitz.Page) -> List:
    markups = []
    texts = []
    squares = []

    annot = page.first_annot

    num_free_text = 0

    while annot:
        if annot.type[0] == fitz.PDF_ANNOT_FREE_TEXT:
            num_free_text += 1
        annot = annot.next

    annot = page.first_annot

    while annot:
        if annot.type[0] in [fitz.PDF_ANNOT_HIGHLIGHT, fitz.PDF_ANNOT_UNDERLINE, fitz.PDF_ANNOT_STRIKE_OUT]:
            markup = get_markups(annot, intersect_threshold=0.9)
            markups.append(markup)
        elif annot.type[0] in [fitz.PDF_ANNOT_TEXT, fitz.PDF_ANNOT_FREE_TEXT]:
            text = get_texts(annot, num_free_text=num_free_text)
            texts.append(text)
        elif annot.type[0] == fitz.PDF_ANNOT_SQUARE and not annot.colors['fill']:
            square = get_squares(annot, num_free_text=num_free_text, intersect_threshold=0.9)
            squares.append(square)
        else:
            pass
        annot = annot.next

    markups = process_markups(markups, page)
    annots = markups + texts + squares
    annots.sort(key=(lambda x: [x[2][0], x[2][1]]))

    return annots


def print_text_mode(markdown: str, annots: List, output: str, page: int, footnotes_num: int, position: str, input_path: str, imagefolder: str) -> (str, int):
    if not annots:
        return markdown, footnotes_num
    for annot in annots:
        if annot[1] in [fitz.PDF_ANNOT_UNDERLINE, fitz.PDF_ANNOT_FREE_TEXT]:
            markdown += annot[0] + '\n\n'
        elif annot[1] == fitz.PDF_ANNOT_TEXT:
            markdown += '[^' + output + '_' + str(footnotes_num) + ']\n\n[^' + output + '_' + str(footnotes_num) + ']: ' + annot[0] + '\n\n'
            footnotes_num += 1
        elif annot[1] == fitz.PDF_ANNOT_SQUARE:
            image_name = output + '_' + str(page) + '_' + str(round(annot[3].x0)) + '_' + str(round(annot[3].y0))
            if imagefolder:
                image_path = os.path.join(imagefolder, image_name) + '.png'
                folder = os.path.join(os.path.join(input_path, output), imagefolder)
                if not os.path.exists(folder):
                    os.mkdir(folder)
            else:
                image_path = image_name + '.png'
            if annot[4]:
                markdown += '![' + annot[4] + '](' + image_path + ')\n\n'
            else:
                markdown += '![' + image_name + '](' + image_path + ')\n\n'
            image_path = os.path.join(os.path.join(input_path, output), image_path)
            annot[0].save(image_path)

    if position == 'page':
        markdown += '—— Page ' + str(page) + ' ——\n\n'
    elif position == 'docpage' or position == 'pagedoc':
        markdown += '—— ' + output + ' - Page ' + str(page) + ' ——\n\n'

    return markdown, footnotes_num


def AnnoDown():

    def dir_path(string):
        if os.path.exists(string):
            return string
        else:
            raise FileNotFoundError(string)

    parser = argparse.ArgumentParser(description="AnnoDown")
    parser.add_argument('input', type=dir_path, help='PDF Path')
    parser.add_argument('--output', '-o', type=str, required=False, help='Output filename (str)')
    parser.add_argument('--position', '-p', type=str.lower, choices=['no', 'none', 'pagedoc', 'docpage', 'page'], default='page', help="Messages added to the markdown file after processing each page that has at least one annotation. Options are 'none' (no message), 'page' (page number) and 'docpage' (output name and page number).")
    parser.add_argument('--imagefolder', '-i', type=str, default='media', help='The name of the folder that stores extracted images. If None, images will be saved at the same directory as the markdown file.')
    parser.add_argument('--start', '-s', type=int, required=False, help='Extract annotations from page x of the PDF file. (The first page is page 1.)')
    parser.add_argument('--end', '-e', type=int, required=False, help='Extract annotations to page x of the PDF file. (The first page is page 1.)')
    # parser.add_argument('--mode', '-m', type=str.lower, choices=['text'], default='text')
    # parser.add_argument('--column', '-c', type=int, default=1)
    # parser.add_argument('--width', '-w', type=float, nargs='+', default=0.0)
    # parser.add_argument('--width-odd', '-wo', type=float, nargs='+', default=0.0)
    # parser.add_argument('--width-even', '-we', type=float, nargs='+', default=0.0)
    parser.add_argument('--overwrite', '-ow', action='store_true', help='Force overwriting the WHOLE output folder even if it already exists and contains something.')
    args = parser.parse_args()

    doc = fitz.open(args.input)
    page_count = doc.page_count
    start = 0
    end = page_count

    if args.start:
        start = args.start - 1
    if args.end:
        end = args.end

    (input_path, input_file) = os.path.split(args.input)
    (output, _) = os.path.splitext(input_file)

    if args.output:
        output = args.output

    path = os.path.join(input_path, output)

    if os.path.exists(path):
        if os.listdir(path):
            print("Directory already exists: " + path)
            if args.overwrite:
                print("Overwriting the folder...")
            else:
                print("Exportation stopped. Use -ow parameter to overwrite.")
                return
    else:
        os.mkdir(path)

    print("Processing: " + output + '\n')

    def print_info(annots_num: int):
        if annots_num == 0:
            print(end='\r')
        elif annots_num == 1:
            print("1 annotation")
        elif annots_num > 1:
            print(str(annots_num) + " annotations")

    markdown = ''
    footnotes = 1

    for i in range(start, end):
        page = doc[i]
        print("Page " + str(i+1) + ": ", end="")
        annots = get_annots(page)
        markdown, footnotes = print_text_mode(markdown, annots, output, i+1, footnotes, args.position, input_path, args.imagefolder)
        print_info(len(annots))

    markdown_name = output + '.md'
    markdown_path = os.path.join(os.path.join(input_path, output), markdown_name)
    if markdown:
        with open(markdown_path, 'w') as f:
            f.write(markdown.strip('\n'))

        print('                              ', end='\r')
        print("\nSuccessfully exported.")
        print("Output path: " + path)
    else:
        print("No supportive annotations found.")
        print("Empty folder: " + path)

if __name__ == "__main__":
    AnnoDown()
