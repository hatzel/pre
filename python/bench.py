#!/bin/python3
import subprocess
import queue
import sqlite3
import threading

THREAD_COUNT = 4
QUEUE_MAXSIZE = 5
DATABASE_FILE = "data.db"

file_queue = queue.Queue(QUEUE_MAXSIZE)


def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("""create table if not exists benchmarks
              (filename text, codec text, version text, args text,
              e_time INTEGER, input_size INTEGER, output_size INTEGER,
              e_iters INTEGER, d_time INTEGER, d_output_size INTEGER,
              d_iters INTEGER);""")
    conn.commit()
    c.close()
    conn.close()
    print("initialized db")


def save(line, db_conn, file_name):
    if line.startswith(("Codec,", "Iterations,", "Overhead iterations,")):
        return
    values = line.strip().split(",")
    q_str = "insert into benchmarks values (" + "'" + file_name + "' "
    for i, v in enumerate(values):
        if len(v) > 0 and i >= 3:
            q_str = q_str + ", " + v
        elif len(v) > 0 and i < 3:
            q_str = q_str + ", " + "'" + v + "'"
        else:
            q_str = q_str + ", " + "'NULL'"
    q_str = q_str + ");"
    print(q_str)
    c = db_conn.cursor()
    c.execute(q_str)
    db_conn.commit()
    c.close()


def worker():
    conn = sqlite3.connect(DATABASE_FILE)
    while True:
        # A little dirty since we just terminate on the empty-exception
        # Should work reliably since the main process
        # generates jobs much faster then worker-threads can process it
        try:
            file_path = file_queue.get(timeout=1)
        except queue.Empty:
            return
        print("benchmarking: " + file_path)
        p = subprocess.Popen(["/home/hansole/bin/fsbench", "-c", file_path],
                             stdout=subprocess.PIPE)
        for line in p.stdout:
            save(line.decode("utf-8"), conn, file_path)

for i in range(THREAD_COUNT):
    print("launching thread " + str(i))
    threading.Thread(target=worker).start()

files = subprocess.Popen(["find", ".", "-type", "f", "-not", "-empty"],
                         stdout=subprocess.PIPE)

for file_location in files.stdout:
    file_queue.put(file_location.decode("utf-8").strip())
