#!/usr/bin/env python3
import matplotlib.pyplot as plt
import sqlite3
import argparse
from tabulate import tabulate

AXIS_LABLES = {
    "e_speed": "Compression speed MByte/s",
    "d_speed": "Decompression speed MByte/s",
    "ratio": "Compression Ratio",
    "block_size": "Filesystem block size"
}
CONVERSION_RATIOS = {
    "e_speed": 1/1000,
    "d_speed": 1/1000,
    "block_size": 1/1000000
}
parser = argparse.ArgumentParser(description="""Visualize the results of your
                                 benchmarks from a sqlite database. Currently
                                 only averages of two metrics from multiple
                                 algorithms can be compared.""")
parser.add_argument("--db-file", dest="database", default="benchmark.db",
                    help="""path to the database containing the data
                    you wish to visualize""")
parser.add_argument("--size_min", help="Filter for minimum filesize in bytes",
                    default=0)
parser.add_argument("--size_max", help="Filter for maximum filesize in bytes",
                    default=-1)
parser.add_argument("xaxis", help="The metric displayed on the x-axis",
                    nargs="?", default="ratio")
parser.add_argument("yaxis", help="The metric displayed on the y-axis",
                    nargs="?", default="e_speed")
parser.add_argument("label", help="""The metric displayed as the label on
                    the data points""", nargs="?", default="codec")
parser.add_argument("--pattern", help="""Only take files into account
                    where filename matches the given pattern.
                    %% can be used as a wildcard.""")
parser.add_argument("-a", dest="algorithms", action="append", help="""Algorithms
                    to query data for. Can be given multiple times. If not
                    given, all available data will be used.""")
parser.add_argument("--table", help="""Specify a file to which
                    to append the data as a latex tabular.""")
parser.add_argument("--no-group-by-algorithm", dest="grouping",
                    action="store_false", help="""Disables gouping of plot points by algorithms.""")
parser.set_defaults(grouping=True)
args = parser.parse_args()


class Plotter():
    """This class creates a scatter plot from given metrics"""
    def __init__(self, x, y, label):
        self.x_name = x
        self.y_name = y
        self.label_name = label
        where_clause = "WHERE input_size >" + str(args.size_min)
        if int(args.size_max) > -1:
            where_clause = where_clause + " AND input_size <"
            + str(args.size_max)
        if args.pattern is not None:
            where_clause = where_clause + " AND filename LIKE " + "'" + args.pattern + "'"
        if args.algorithms is not None:
            where_clause = where_clause + " AND codec IN (" + ",".join(list(map(lambda s: '"' + s + '"', args.algorithms))) + ")"

        group_clause = ""
        x_str = x
        y_str = y
        if args.grouping:
            group_clause = "GROUP by " + label
            x_str = "avg(" + x + ")"
            y_str = "avg(" + y + ")"
        q_str_avg = """SELECT {0}, {1}, {2} FROM benchmarks
            {3} {4};""".format(label, x_str, y_str, where_clause, group_clause)
        conn = sqlite3.connect(args.database)
        c = conn.cursor()
        print(q_str_avg)
        c.execute(q_str_avg)
        self.data = [list(i) for i in c]
        self.x = [row[1] for row in self.data]
        self.y = [row[2] for row in self.data]
        self.label = [row[0] for row in self.data]

        print(self.x)
        print(self.y)
        print(self.label)

        self.convert_units()

    def convert_units(self):
        self.x = list(map(
            lambda i: conversion_factor(self.x_name) * i,
            self.x))
        self.y = list(map(
            lambda i: conversion_factor(self.y_name) * i,
            self.y))
        if conversion_factor(self.label_name) != 1:
            self.label = list(map(
                lambda i: conversion_factor(self.label_name) * float(i),
                self.label))

    def draw(self):
        plt.scatter(self.x, self.y, marker='x')
        for d in zip(self.label, self.x, self.y):
            plt.annotate(d[0], (d[1], d[2]), xytext=(-10, 10),
                         textcoords = 'offset points')
        plt.xlabel(get_label(self.x_name))
        plt.ylabel(get_label(self.y_name))
        plt.show()

    def get_data(self, fmt):
        header = map(get_label, [self.label_name, self.x_name, self.y_name])
        return tabulate([list(i) for i in zip(*[self.label, self.x, self.y])],
                        header,
                        floatfmt=".2f",
                        tablefmt=fmt)


def conversion_factor(unit):
    return CONVERSION_RATIOS.get(unit, 1)


def get_label(name):
    return AXIS_LABLES.get(name, "Unknown Metric")

p = Plotter(args.xaxis, args.yaxis, args.label)
if args.table:
    with open(args.table, "a") as f:
        f.write("\n%%Data from " + str(args.database) +
                ", filtered with: " + str(args.pattern) + "\n")
        f.write(str(p.get_data("latex")))
else:
    print(p.get_data("plain"))
p.draw()
