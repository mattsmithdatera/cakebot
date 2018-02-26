#!/usr/bin/env python

from __future__ import print_function, unicode_literals, division

import functools
import json
import re
import collections

import requests

from dateutil.parser import parse as dparse

BASE_URL = "https://review.openstack.org/changes/?q=%s"


def consume(it):
    collections.deque(it, 0)


def greq(**kwargs):
    gfilter = []
    options = []
    if "options" in kwargs:
        options = kwargs.pop("options")
    for k, v in kwargs.items():
        gfilter.append('%s:{%s}' % (k, v))
    url = BASE_URL % ' AND '.join(gfilter)
    if options:
        parts = [url]
        options = map(lambda x: "o=" + x.upper(), options)
        parts.extend(options)
        url = "&".join(parts)
    resp = requests.get(url)

    return json.loads(resp.text[4:])


def get_merged(author):
    return greq(owner="%s" % author, status='merged')


def get_abandoned(author):
    return greq(owner="%s" % author, status='abandoned')


def earliest_merged(merged):
    return merged[-1]['submitted'].split()[0]


def open_review(merged):
    longest = None
    for review in merged:
        d1 = dparse(review['created'])
        d2 = dparse(review['submitted'])
        dt = d2 - d1
        if not longest or dt > longest:
            longest = dt
    return longest.days


def lines_added(merged):
    return sum(map(lambda x: x['insertions'], merged))


def lines_deleted(merged):
    return sum(map(lambda x: x['deletions'], merged))


def projects(merged):
    found = set()
    consume(map(lambda x: found.add(x['project']), merged))
    return "\n\t".join(list(sorted(found)))


def projects_stats(merged):
    found = {}
    total = len(merged)

    phelper = functools.partial(_count_helper, key='project', data=found)

    consume(map(phelper, merged))
    for f in found:
        found[f] = "-- " + str(round((found[f] / total) * 100, 2)) + "%"
    return "\n\t".join(list(map(" ".join, sorted(found.items()))))


def comment_stats(comments):
    counts = {}
    chelper = functools.partial(
        _comment_count_helper, key='messages', data=counts)
    for review in comments:
        consume(map(chelper, comments))
    return sorted(
        filter(lambda x: not x[0].startswith("http"), counts.items()),
        key=lambda x: x[1], reverse=True)[:20]


def stats(author):
    merged = get_merged(author)
    abandoned = get_abandoned(author)
    return "\n".join(["Cake Day: %s" % earliest_merged(merged),
                      "Num Merged: %s" % len(merged),
                      "Num Abandoned: %s" % len(abandoned),
                      "Longest Open Merged Review: %s" % open_review(merged),
                      "Lines Added: %s" % lines_added(merged),
                      "Lines Deleted: %s" % lines_deleted(merged),
                      "Projects: %s" % projects_stats(merged)])


def _count_helper(x, key, data):
    if x[key] in data:
        data[x[key]] += 1
    else:
        data[x[key]] = 1

# BANNED_EQ = ["patch", "Uploaded"]
BANNED_EQ = []
BANNED_SW = []
CI_RE = re.compile("^(.* CI|Jenkins|Zuul)$")


def _ffunc(x):
    # if (len(x) < 4 or x in BANNED_EQ or
    #         any((x.startswith(sw) for sw in BANNED_SW))):
    #     return False
    return True


def _comment_count_helper(x, key, data):
    comments = x[key]
    tot_messages = reduce(
        lambda x, y: " ".join((x,
                              (y['message']
                               if 'author' in y.keys() and
                               not CI_RE.match(y['author']['name'])
                               else ""))),
        comments, "")
    for word in filter(_ffunc, tot_messages.split()):
        if word in data:
            data[word] += 1
        else:
            data[word] = 1
