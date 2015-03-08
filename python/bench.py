#!/bin/python3
import subprocess
from multiprocessing import Pool
import sqlite3
import argparse
import sys


class StopMarker:
    """Object in queue that tells the worker-threads that
    they have reached the workloads end"""
    pass


def init_db():
    conn = sqlite3.connect(args.database)
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


def save_line(line, file_name):
    db_conn = sqlite3.connect(args.database)
    if line.startswith(("Codec,", "Iterations,", "Overhead iterations,")):
        return True
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


def save(result):
    for i, line in enumerate(result["output"]):
        save_line(line, result["file"])


def worker(file_path):
    print("benchmarking: " + file_path)
    p = subprocess.check_output([args.fsbench] + ALGORITHMS
                                + ["-c", file_path], universal_newlines=True)
    p = p.split("\n")
    return {"output": p[1:-4], "file": file_path}


def sigint_handler(signal, frame):
    sys.exit(1)


def log_error(e):
    print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Run fsbench on a large number of files.
                                    The results are stored ina sqlite3
                                    database.""")

    parser.add_argument("directory", metavar="root_dir",
                        help="The root directory to be benchmarked",
                        default=".")
    parser.add_argument("--db-file", dest="database", default="benchmark.db",
                        help="""Where to store the sqlite
                        database with the results""")
    parser.add_argument("algorithms", metavar="algorithms", nargs="*",
                        help="Algorithms to pass on to fsbench")
    parser.add_argument("--fsbench", dest="fsbench", default="fsbench",
                        help="""Path to your fsbench executable.
                        The default is ./fsbench""")
    parser.add_argument("-t", "--threads", dest="threads", default=4, type=int,
                        help="Number of worker threads compressing files.")
    args = parser.parse_args()

    THREAD_COUNT = args.threads
    QUEUE_MAXSIZE = 5
    ROOT_DIR = args.directory

    init_db()

    if args.algorithms is not None:
        ALGORITHMS = args.algorithms
    else:
        ALGORITHMS = []

    pool = Pool(processes=args.threads)

    files = subprocess.Popen(["find", ROOT_DIR, "-type", "f",
                              "-not", "-empty"],
                             stdout=subprocess.PIPE)

    for file_location in files.stdout:
        pool.apply_async(worker, (file_location.decode("utf-8").strip(),),
                         callback=save, error_callback=log_error)

    pool.close()
    pool.join()
