# -*- coding: utf-8 -*-


def subseteq(list1, list2):
    # return set(list1).issubset(set(list2))
    list1 = list(list1)
    list2 = list(list2)
    for i in list1:
        if not i in list2:
            return False
    return True


def flat(list_of_list):
    return sum(list(list_of_list), [])


def update(list1, list2):
    count = 0
    for item in list2:
        if item not in list1:
            list1.append(item)
            count += 1
    return count

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }


def html_escape(text):
    return "".join(html_escape_table.get(c, c) for c in text)
