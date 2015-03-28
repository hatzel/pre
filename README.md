# pre

This repository contains the results of our university project
"Parallelrechnerevaluation".

In this project, we evaluated compression algorithms regarding their application
in hpc storage systems. For this we used the FOSS tool
[fsbench](https://chiselapp.com/user/Justin_be_my_guide/repository/fsbench/)
(potentially outdated git mirror [here](https://github.com/Ahti/fsbench/)) and a
set of scripts developed by us specifically for this task.

The folder `python` contains the two scripts we developed. The report we wrote is located in the folder `Bericht`.

## scripts

`bench.py` uses fsbench to test a set of algorithms with multiple files and
writes the results into a sqlite database.

`plot.py` is used to output the data in the sqlite database in a human-readable
way, either as graphs or LaTeX tables.
