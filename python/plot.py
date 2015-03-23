#!/usr/bin/env python3
import matplotlib.pyplot as plt
import sqlite3
import argparse

AXIS_LABLES = {
    "e_speed": "Compression speed MByte/s",
    "d_speed": "Decompression speed MByte/s",
    "ratio": "Compression Ratio"
}
parser = argparse.ArgumentParser(description="""Visualize the results of your
                                 benchmarks from a sqlite database. Currently
                                 only averages of two metrics from multiple
                                 algorithms can be compared.""")
parser.add_argument("--db-file", dest="database", default="benchmark.db",
                    help="""path to the database containing the data
                    you wish to visualize""")
parser.add_argument("--size_min", help="Filter for minimum filesize in bytes",
                    default=-1)
parser.add_argument("--size_max", help="Filter for maximum filesize in bytes",
                    default=-1)
parser.add_argument("xaxis", help="The metric displayed on the x-axis",
                    nargs="?", default="ratio")
parser.add_argument("yaxis", help="The metric displayed on the y-axis",
                    nargs="?", default="e_speed")
parser.add_argument("--pattern", help="""Only take files into account
                    where filename matches the given pattern.
                    '%' can be used as a wildcard.""")
args = parser.parse_args()

where_clause = "WHERE input_size >" + str(args.size_min)
if int(args.size_max) > -1:
    where_clause = where_clause + " AND input_size <" + str(args.size_max)
if args.pattern is not None:
    print(args.pattern)
    where_clause = where_clause +  " AND filename LIKE " + "'" + args.pattern + "'"
q_str_avg = """SELECT codec, avg({0}), avg({1}) FROM benchmarks
            {2} GROUP by codec;""".format(args.xaxis, args.yaxis, where_clause)

conn = sqlite3.connect(args.database)
c = conn.cursor()
print(q_str_avg)
c.execute(q_str_avg)
data = [list(i) for i in c]


def convert_units():
    if args.xaxis == "e_speed":
        dataT[1] = list(map((lambda x: x / 1000), dataT[1]))
    elif args.yaxis == "e_speed":
        dataT[2] = list(map((lambda x: x / 1000), dataT[2]))
    pass


def get_label(name):
    try:
        return AXIS_LABLES[name]
    except KeyError:
        return "Unknown Metric"
# Transpose the data matrix
dataT = [[d[i] for d in data] for i in range(3)]
convert_units()
# The conversion of  units only works on the translated matix
# Since we want to keep the correction we need to translate again
data = [[d[i] for d in dataT] for i in range(len(data))]
plt.scatter(dataT[1], dataT[2])

for d in data:
    print(d[0])
    plt.annotate(d[0], (d[1], d[2]), xytext=(-10, 10),
                 textcoords = 'offset points')
plt.xlabel(get_label(args.xaxis))
plt.ylabel(get_label(args.yaxis))
plt.show()
