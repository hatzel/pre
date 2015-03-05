#!/bin/bash
find . -type f -not -empty -exec echo {} \; -exec fsbench $@ {} \;
