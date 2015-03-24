#!/usr/bin/env python3
import subprocess
from multiprocessing import Pool
import sqlite3
import argparse


def init_db():
    conn = sqlite3.connect(args.database)
    c = conn.cursor()
    c.execute("""create table if not exists benchmarks
              (filename text, codec text, version text, args text,
              e_time INTEGER, input_size INTEGER, output_size INTEGER,
              e_iters INTEGER, d_time INTEGER, d_output_size INTEGER,
              d_iters INTEGER, ratio REAL,
              e_speed INTEGER, d_speed, block_size);""")
    conn.commit()
    c.close()
    conn.close()


def calculate_ratio(a, b):
    """Calculates a/b and returns the result as a string. For easy handling
    ins sqlite query strings"""
    if a == "":
        a = 0
    if b == "":
        b = 0
    a = int(a)
    b = int(b)
    if b == 0:
        return "NULL"
    else:
        return str(float(a) / float(b))


def save_line(line, file_name, db_conn):
    if line.startswith(("Codec,", "Iterations,", "Overhead iterations,")):
        return
    values = line.strip().split(",")
    # Appending Compression Ration
    values.append(calculate_ratio(values[4], values[5]))
    # Appending encoding speed
    values.append(calculate_ratio(values[4], values[3]))
    # Appending decoding speed
    values.append(calculate_ratio(values[8], values[7]))
    # Append block size
    values.append(args.blocksize)
    q_str = "insert into benchmarks values (" + "'" + file_name + "' "
    for i, v in enumerate(values):
        if len(v) > 0 and i >= 3:
            q_str += ", " + v
        elif len(v) > 0 and i < 3:
            q_str += ", " + "'" + v + "'"
        else:
            q_str += ", " + "NULL"
    q_str += ");"
    if __debug__:
        print(q_str)
    c = db_conn.cursor()
    c.execute(q_str)
    db_conn.commit()
    c.close()


def save(result):
    db_conn = sqlite3.connect(args.database)
    for i, line in enumerate(result["output"]):
        save_line(line, result["file"], db_conn)
    db_conn.close()


def worker(file_path):
    if __debug__:
        print("benchmarking: " + file_path)
    p = subprocess.check_output([args.fsbench] + args.algorithms
                                + ["-b" + args.blocksize, "-c",
                                   "-w0", file_path],
                                universal_newlines=True)
    p = p.split("\n")
    # The array slice removes the meta information given by fsbench.
    return {"output": p[1:-4], "file": file_path}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Run fsbench on a large number of files.
                                    The results are stored in a sqlite3 database.
                                    All units in the database are in bytes
                                    and milliseconds""")

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
    parser.add_argument("-p", "--processes", dest="processes", default=None,
                        type=int,
                        help="""Number of worker processes compressing files.
                        This defaults to the number of your
                        processor cores.""")
    parser.add_argument("-b", dest="blocksize", default="1717986918",
                        help="""filesystem block size to be
                        passed on to fsbench.""")
    args = parser.parse_args()

    init_db()

    pool = Pool(processes=args.processes)

    files = subprocess.Popen(["find", args.directory, "-type", "f",
                              "-not", "-empty"],
                             stdout=subprocess.PIPE)

    file_count = 0
    for file_location in files.stdout:
        file_count += 1
        pool.apply_async(worker, (file_location.decode("utf-8").strip(),),
                         callback=save)

    pool.close()
    pool.join()
