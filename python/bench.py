#!/bin/python
import subprocess
import Queue
import sqlite3

QUEUE_MAXSIZE = 5

file_queue = Queue(QUEUE_MAXSIZE)


def save(line, db_connection):
    if line.startswith(("Codec,", "Iterations,", "Overhead iterations,")):
        return
    values = line.strip().split(",")
    q_str = "insert into benchmarks values ("
    for v in values:
        if len(v) > 0:
            q_str = q_str + "," + v
        else:
            q_str = q_str + "'NULL'"


def worker():
    conn = sqlite3.connect("data.db")
    while True:
        file_path = file_queue.deque()
        p = subprocess.Popen("fsbench -c " + file_path,
                             stdout=subprocess.PIPE, shell=True)
        for line in p.stdout:
            save(line, conn)

"""
def launch_benchmark(file_path):
    file_path = file_path.decode("utf-8")
    p = subprocess.Popen("fsbench -c " + file_path,
                         stdout=subprocess.PIPE, shell=True)
    for x in p.stdout:
        print(x)
"""
files = subprocess.Popen("find . -type f -not -empty -exec echo {} \;",
                         stdout=subprocess.PIPE, shell=True)

for file_location in files.stdout:
    file_queue.put(file_location.decode("utf-8"))
