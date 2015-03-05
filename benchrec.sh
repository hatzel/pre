#!/bin/bash
find . -type f -exec fsbench "$@" {} \;
