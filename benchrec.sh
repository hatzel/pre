#!/bin/bash
echo "Used codec,version,args,E.time (ms),E. input size,E. output size,E. iters,D. time(ms),D. output size,D. iters"
name=""
find . -type f -not -empty -exec echo {} \; -exec fsbench $@ {} \; | sed "/^.*terations.*/d;/^Codec/d"
