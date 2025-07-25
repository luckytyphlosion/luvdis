# Code licensed LGPLv3 by Jérémie Lumbroso <lumbroso@cs.princeton.edu>

# some changes made by luckytyphlosion
# specific to diffing ai script dumps
# those changes are under MIT

import latest_difflib
import itertools
import textwrap
import typing
import re

# space TAB
SAB = "        "

def side_by_side(
    left: typing.List[str],
    right: typing.List[str],
    width: int = 78,
    as_string: bool = False,
    separator: typing.Optional[str] = " | ",
    left_title: typing.Optional[str] = None,
    right_title: typing.Optional[str] = None,
) -> typing.Union[str, typing.List[str]]:
    """Returns either the list of lines, or string of lines, that results from
    merging the two lists side-by-side.
    :param left: Lines of text to place on the left side
    :type left: typing.List[str]
    :param right: Lines of text to place on the right side
    :type right: typing.List[str]
    :param width: Character width of the overall output, defaults to 78
    :type width: int, optional
    :param as_string: Whether to return a string (as opposed to a list of strings), defaults to False
    :type as_string: bool, optional
    :param separator: String separating the left and right side, defaults to " | "
    :type separator: typing.Optional[str], optional
    :param left_title: Title to place on the left side, defaults to None
    :type left_title: typing.Optional[str], optional
    :param right_title: Title to place on the right side, defaults to None
    :type right_title: typing.Optional[str], optional
    :return: Lines or text of the merged side-by-side output.
    :rtype: typing.Union[str, typing.List[str]]
    """

    DEFAULT_SEPARATOR = " | "
    separator = separator or DEFAULT_SEPARATOR

    mid_width = (width - len(separator) - (1 - width % 2)) // 2

    tw = textwrap.TextWrapper(
        width=mid_width,
        break_long_words=False,
        replace_whitespace=False
    )

    def reflow(lines):
        wrapped_lines = list(map(tw.wrap, lines))
        wrapped_lines_with_linebreaks = [
            [""] if len(wls) == 0 else wls
            for wls in wrapped_lines
        ]
        return list(itertools.chain.from_iterable(wrapped_lines_with_linebreaks))

    left = reflow(left)
    right = reflow(right)

    zip_pairs = itertools.zip_longest(left, right)
    if left_title is not None or right_title is not None:
        left_title = left_title or ""
        right_title = right_title or ""
        zip_pairs = [
            (left_title, right_title),
            (mid_width * "-", mid_width * "-")
        ] + list(zip_pairs)

    lines = []
    for l, r in zip_pairs:
        l = l or ""
        r = r or ""
        line = "{}{}{}{}".format(
            l,
            (" " * max(0, mid_width - len(l))),
            separator,
            r
        )
        lines.append(line)

    if as_string:
        return "\n".join(lines)

    return lines

branch_bytes_regex = re.compile(rf"{SAB}\.byte 0x[0-9a-fA-F]+, 0xE0")
cond_branch_label_regex = re.compile(rf"{SAB}b(eq|ne|gt|ge|lt|le) (\.label\d+)")
cond_branch_lclabel_regex = re.compile(rf"{SAB}b(eq|ne|gt|ge|lt|le) (\.lclabel\d+)")
beq_label_regex = re.compile(rf"{SAB}beq (\.label\d+)")
bne_label_regex = re.compile(rf"{SAB}bne (\.label\d+)")
bgt_label_regex = re.compile(rf"{SAB}bgt (\.label\d+)")
bge_label_regex = re.compile(rf"{SAB}bge (\.label\d+)")
blt_label_regex = re.compile(rf"{SAB}blt (\.label\d+)")
ble_label_regex = re.compile(rf"{SAB}ble (\.label\d+)")

branch_cond_to_inverse_cond_regex = {
    "eq": bne_label_regex,
    "ne": beq_label_regex,
    "gt": ble_label_regex,
    "ge": blt_label_regex,
    "lt": bge_label_regex,
    "le": bgt_label_regex,
}

pool_branch_regex = re.compile(rf"{SAB}b (\.p?label\d+)")
branch_regex = re.compile(rf"{SAB}b (\.label\d+)")
super_long_branch_regex = re.compile(rf"{SAB}bl (\.label\d+)")

unused_2_bytes_regex = re.compile(rf"{SAB}\.byte 0x[0-9A-Fa-f]+, 0x[0-9A-Fa-f]+")

#beq_lclabel_regex = re.compile(rf"{SAB}beq .lclabel(\d+)")
#bne_lclabel_regex = re.compile(rf"{SAB}bne .lclabel(\d+)")
#bgt_lclabel_regex = re.compile(rf"{SAB}bgt .lclabel(\d+)")
#bge_lclabel_regex = re.compile(rf"{SAB}bge .lclabel(\d+)")
#blt_lclabel_regex = re.compile(rf"{SAB}blt .lclabel(\d+)")
#ble_lclabel_regex = re.compile(rf"{SAB}ble .lclabel(\d+)")
#
#lc_branch_cond_to_inverse_cond_regex = {
#    "eq": beq_lclabel_regex,
#    "ne": bne_lclabel_regex,
#    "gt": bgt_lclabel_regex,
#    "ge": bge_lclabel_regex,
#    "lt": blt_lclabel_regex,
#    "le": ble_lclabel_regex,
#}

# non-functional, has side effects
# returns # of lines to advance
def try_ignore_long_conditional_branch_diff_and_pool_branch(left_side, right_side, index):
    #if index + 4 > len(left_side):
    #    return 1

    
    #    print(f"left_side[index]: {left_side[index]}")


    # check - signs first because they're easy to check
    if left_side[index] == "-" and right_side[index + 1] == "-" and left_side[index + 2] == "-":
        line_rel_3_equal = (left_side[index + 3] == right_side[index + 3])
        if left_side[index + 3] == "-" or line_rel_3_equal:
            if line_rel_3_equal:
                cond_branch_regex = cond_branch_label_regex
            else:
                cond_branch_regex = cond_branch_lclabel_regex

            if (match_obj := cond_branch_regex.match(right_side[index])):
                #if index == 243:
                #    print("index 243 passed first check")
                branch_cond = match_obj.group(1)
                small_branch_label = match_obj.group(2)
                inverse_cond_regex = branch_cond_to_inverse_cond_regex[branch_cond]
    
                if (match_obj := inverse_cond_regex.match(left_side[index + 1])):
                    cond_label_if_no_long_branch = match_obj.group(1)
                    #if index == 243:
                        #print("index 243 passed second check")
                        #print(f"right_side[index + 2]: {right_side[index + 2]}\nright_side[index + 3]: {right_side[index + 3]}\ncond_label_if_no_long_branch: {cond_label_if_no_long_branch}\nsmall_branch_label: {small_branch_label}")
                        #print(f"right side + 2 first char: {ord(right_side[index + 2][0])}")
                        #print("check1: " + str(right_side[index + 2] == f"{SAB}b {cond_label_if_no_long_branch}"))
    
                    if right_side[index + 2] in {f"{SAB}b {cond_label_if_no_long_branch}", f"{SAB}bl {cond_label_if_no_long_branch}"} and cond_label_if_no_long_branch[0] == "." and right_side[index + 3] == small_branch_label:
                        #print(f"all checks passed")
                        left_side[index] = "*"
                        right_side[index + 1] = "*"
                        left_side[index + 2] = "*"
                        if not line_rel_3_equal:
                            left_side[index + 3] = "*"
                        return index + 4

    # long conditional branch failed, try pool diff
    if left_side[index] == "-" and left_side[index + 1] == "-" and left_side[index + 2] == "-":
        # check the pool branch and the pool itself
        if right_side[index + 1] == f"{SAB}.pool":
            if (match_obj := pool_branch_regex.match(right_side[index])):
                # pool diff can either have two unused bytes or not after the pool
                # check for these
                pool_branch_label = match_obj.group(1)
                if unused_2_bytes_regex.match(right_side[index + 2]):
                    if left_side[index + 3] == "-" and right_side[index + 3] == pool_branch_label:
                        left_side[index] = "*"
                        left_side[index + 1] = "*"
                        left_side[index + 2] = "*"
                        left_side[index + 3] = "*"
                        return index + 4
                    elif left_side[index + 3] == right_side[index + 3] == pool_branch_label:
                        left_side[index] = "*"
                        left_side[index + 1] = "*"
                        left_side[index + 2] = "*"
                        return index + 3
                elif right_side[index + 2] == pool_branch_label:
                    left_side[index] = "*"
                    left_side[index + 1] = "*"
                    left_side[index + 2] = "*"
                    return index + 3
            # super edge case for pool being created right before a func start
            elif branch_bytes_regex.match(right_side[index]) and unused_2_bytes_regex.match(right_side[index + 2]):
                left_side[index] = "*"
                left_side[index + 1] = "*"
                left_side[index + 2] = "*"
                return index + 3

    # checking for super long branch from end of conditional block
    if right_side[index] == "-" and left_side[index + 1] == "-":
        match_obj = branch_regex.match(left_side[index])
        if match_obj:
            branch_label = match_obj.group(1)
            if branch_label[0] == "." and right_side[index + 1] == f"{SAB}bl {branch_label}":
                right_side[index] = "*"
                left_side[index + 1] = "*"
                return index + 2

    return index + 1

def patch_left_side_right_side_diff(left_side, right_side):
    # first line is sometimes the 2 padding bytes required as the first function starts on a non-word aligned address
    # don't track this as a diff
    if left_side[0] == "-" and right_side[0] == f"{SAB}.byte 0x0, 0x0":
        left_side[0] = "*"

    # last two lines are sometimes the final pool and the branch bytes
    # don't track this as a diff
    if left_side[-2] == "-" and left_side[-1] == "-" and branch_bytes_regex.match(right_side[-2]) and right_side[-1] == f"{SAB}.pool":
        left_side[-2] = "*"
        left_side[-1] = "*"

    index = 0

    lines_len_minus_4 = len(left_side) - 4
    
    while index <= lines_len_minus_4:
        index = try_ignore_long_conditional_branch_diff_and_pool_branch(left_side, right_side, index)

    return left_side, right_side

def better_diff(
    left: typing.List[str],
    right: typing.List[str],
    width: int = 78,
    as_string: bool = False,
    separator: typing.Optional[str] = None,
    left_title: typing.Optional[str] = None,
    right_title: typing.Optional[str] = None,
) -> typing.Union[str, typing.List[str]]:
    """Returns a side-by-side comparison of the two provided inputs, showing
    common lines between both inputs, and the lines that are unique to each.
    :param left: Lines of text to place on the left side
    :type left: typing.List[str]
    :param right: Lines of text to place on the right side
    :type right: typing.List[str]
    :param width: Character width of the overall output, defaults to 78
    :type width: int, optional
    :param as_string: Whether to return a string (as opposed to a list of strings), defaults to False
    :type as_string: bool, optional
    :param separator: String separating the left and right side, defaults to " | "
    :type separator: typing.Optional[str], optional
    :param left_title: Title to place on the left side, defaults to None
    :type left_title: typing.Optional[str], optional
    :param right_title: Title to place on the right side, defaults to None
    :type right_title: typing.Optional[str], optional
    :return: Lines or text of the merged side-by-side diff comparison output.
    :rtype: typing.Union[str, typing.List[str]]
    """

    differ = latest_difflib.Differ()

    left_side = []
    right_side = []

    # adapted from
    # LINK: https://stackoverflow.com/a/66091742/408734
    difflines = list(differ.compare(left, right))

    #with open("betterdiff_difflines.dump", "w+") as f:
    #    f.write("\n".join(difflines) + "\n")

    longest_len = 0

    for i, line in enumerate(difflines):
        op = line[0]
        tail = line[2:]
        if tail[0] == "\t":
            tail = f"{SAB}{tail[1:]}"

        tail_len = len(tail)
        if tail_len > longest_len:
            longest_len = tail_len

        if op == " ":
            # line is same in both
            left_side.append(tail)
            right_side.append(tail)

        elif op == "-":
            # line is only on the left
            left_side.append(tail)
            right_side.append("-")

        elif op == "+":
            # line is only on the right
            left_side.append("-")
            right_side.append(tail)

    #with open("betterdiff_leftside.dump", "w+") as f:
    #    f.write("\n".join(left_side) + "\n")
    #
    #with open("betterdiff_rightside.dump", "w+") as f:
    #    f.write("\n".join(right_side) + "\n")

    left_side, right_side = patch_left_side_right_side_diff(left_side, right_side)

    num_diffs = 0

    for left_line, right_line in zip(left_side, right_side):
        if left_line == "-" or right_line == "-":
            num_diffs += 1

    if width == -1:
        width = (longest_len + 2) * 2

    return num_diffs, side_by_side(
        left=left_side,
        right=right_side,
        width=width,
        as_string=as_string,
        separator=separator,
        left_title=left_title,
        right_title=right_title,
    )
