#!/usr/bin/env python3
import subprocess
from multiprocessing import Pool
import sqlite3
import argparse


def init_db():
    conn = sqlite3.connect(args.database)
    c = conn.cursor()
    c.execute("""create table if not exists benchmarks
              (filename TEXT, codec TEXT COLLATE NOCASE,
              version TEXT, args TEXT,
              e_time INTEGER, input_size INTEGER, output_size INTEGER,
              e_iters INTEGER, d_time INTEGER, d_output_size INTEGER,
              d_iters INTEGER, ratio REAL,
              e_speed INTEGER, d_speed INTEGER, block_size INTEGER);""")
    c.execute("create index if not exists fileindex on benchmarks (filename, block_size);")
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
    values = [file_name] + line.strip().split(",")
    # Appending Compression Ration
    values.append(calculate_ratio(values[5], values[6]))
    # Appending encoding speed
    values.append(calculate_ratio(values[5], values[4]))
    # Appending decoding speed
    values.append(calculate_ratio(values[9], values[8]))
    # Append block size
    values.append(args.blocksize)
    for i, v in enumerate(values):
        if len(v) <= 0:
            values[i] = "NULL"
    c = db_conn.cursor()
    c.execute("""insert into benchmarks values
              (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);""", tuple(values))
    db_conn.commit()
    c.close()


def entry_exists_for_blocksize(db_conn, filename):
    c = db_conn.cursor()
    c.execute("""select * from benchmarks where
              filename like ? and block_size = ?""",
              (filename, args.blocksize))
    db_conn.commit()
    if not c.fetchone():
        c.close()
        return False
    else:
        c.close()
        return True


def algorithms_logged_for_file(db_conn, filename):
    c = db_conn.cursor()
    c.execute("""select codec from benchmarks
              where filename = ? and block_size = ?""",
              (filename, args.blocksize))
    db_conn.commit()
    algs = c.fetchall()
    algs = [i[0].upper() for i in algs]
    c.close()
    return algs


def save(result):
    db_conn = sqlite3.connect(args.database)
    for i, line in enumerate(result["output"]):
        save_line(line, result["file"], db_conn)
    db_conn.close()


def is_data(line):
    if line.startswith(("Codec,version", "Overhead iterations,", "Iterations,4")):
        return False
    elif len(line) < 5:
        return False
    else:
        return True


def worker(file_path, algorithms):
    if len(algorithms) == 0:
        return {"output": [], "file": file_path}
    if __debug__:
        print("benchmarking: " + file_path)
    try:
        p = subprocess.check_output([args.fsbench] + algorithms
                                    + ["-b" + args.blocksize, "-s0",
                                       "-c", "-w0", file_path],
                                    universal_newlines=True)
    except subprocess.CalledProcessError as e:
        print("fsbench error in process" + str(e.returncode) +
              " while processing file " + file_path)
        p = e.output
    except subprocess.TimeoutExpired:
        print("Timeout Error")
    except Exception:
        print("Unknown error while calling fsbench")
    p = p.split("\n")
    p = [i for i in p if is_data(i)]
    return {"output": p, "file": file_path}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Run fsbench on a large number of files.
                                    The results are stored in a sqlite3
                                     database. All units in the
                                     database are in bytes
                                    and milliseconds.""")

    parser.add_argument("directory", metavar="root_dir",
                        help="The root directory to be benchmarked",
                        default=".")
    parser.add_argument("--db-file", dest="database", default="benchmark.db",
                        help="""Where to store the sqlite
                        database with the results""")
    parser.add_argument("algorithms", metavar="algorithms", nargs="+",
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
    db_conn = sqlite3.connect(args.database)
    for file_location in files.stdout:
        file_count += 1
        file_name = file_location.decode("utf-8").strip()
        algs = algorithms_logged_for_file(db_conn, file_name)
        # Find the algorithms that were not yet measured
        algs = [i for i in args.algorithms if i.upper() not in algs]
        if len(algs) > 0:
            pool.apply_async(worker, (file_name, algs), callback=save)
    db_conn.close()

    pool.close()
    pool.join()
