#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import cPickle
import json
import Queue
import time
import logging
import networkx as nx
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%m-%d-%y %H:%M:%S')

logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


MY_GROUP_ID = 29937606
MY_USER_ID = 144597051

SERVER_URL = "http://ec2-52-17-77-210.eu-west-1.compute.amazonaws.com/method/"
WINDOW_SIZE = 1000

COUNT = requests.get(
    SERVER_URL + "groups.getMembers?scope=super&group_id={0}".format(
        MY_GROUP_ID
    )
).json()["response"]["count"]

build_group_request = lambda d: SERVER_URL + (
    "groups.getMembers?scope=super&group_id={0}&{1}".format(
        MY_GROUP_ID,
        "&".join([
            "=".join([k, str(v)])
            for k, v in d.items()
        ])
    )
)

build_friends_request = lambda _user_id: SERVER_URL + (
    "friends.get?v=5.29&lang=en&user_id={0}".format(_user_id)
)

pages = (
    requests.get(
        build_group_request({
            "offset": WINDOW_SIZE * i,
            "count": WINDOW_SIZE,
        })
    ).json()['response']['items']
    for i in xrange(int(float(COUNT) / WINDOW_SIZE + 1))
)


def get_user_ids():
    ids_dump_filename = "all_ids.pickle"
    if not os.path.exists(ids_dump_filename):
        user_ids = set()
        for i, page in enumerate(pages):
            logger.info("Page {0} from {1}".format(i, int(float(COUNT) / WINDOW_SIZE)))
            for _user_id in page:
                user_ids.add(_user_id)

        with open(ids_dump_filename, "w") as _dump:
            logger.info('dump to file, total %d' % len(user_ids))
            cPickle.dump(user_ids, _dump, cPickle.HIGHEST_PROTOCOL)
    else:
        with open(ids_dump_filename, "r") as _dump:
            user_ids = cPickle.load(_dump)
            logger.info('load from file, total %d' % len(user_ids))
    return user_ids

GRAPH_DUMP_FILENAME = "graph.pickle"
USER_IDS = get_user_ids()

# строим граф
if not os.path.exists(GRAPH_DUMP_FILENAME):

    graph = nx.Graph()
    visited = set()
    __i = 0
    counter = 0
    for user_id in USER_IDS:
        __i += 1

        if __i % 1000 == 0:
            logger.info("%d from %d" % (__i, len(USER_IDS)))

        q = Queue.Queue()
        q.put(user_id)
        while not q.empty():
            current_id = q.get()
            if current_id in visited:
                continue
            counter += 1
            visited.add(current_id)

            res = requests.get(build_friends_request(current_id)).json()
            friends_ids = set(res['response']['items']) & USER_IDS

            logger.info("Found friend N{0}: {1} ({2} friends)".format(counter, current_id, len(friends_ids)))

            for f_id in friends_ids:
                graph.add_node(f_id)
                graph.add_edge(current_id, f_id)
                if f_id not in visited:
                    q.put(f_id)

            if counter % 500 == 0:
                time.sleep(1)

    with open(GRAPH_DUMP_FILENAME, "w") as dump:
        cPickle.dump(graph, dump, cPickle.HIGHEST_PROTOCOL)
else:
    with open(GRAPH_DUMP_FILENAME, "r") as dump:
        graph = cPickle.load(dump)

res = {
    "max": 14,  # 14 nx.eccentricity(graph, MY_USER_ID)
    "mean": 0
}

count = 0
sum_paths = 0
for n in graph.nodes_iter():
    if n == MY_USER_ID:
        continue
    try:
        sum_paths += nx.shortest_path_length(
            graph,
            source=MY_USER_ID,
            target=n
        )
        count += 1
    except nx.NetworkXNoPath:
        continue

res["mean"] = round(float(sum_paths) / count, 10)
print(json.dumps(res))

# {"max": 14, "mean": 5.5441285441}
# {"max": 14, "mean": 5.5582734633}