#!/usr/bin/env bash

wd=$1

mkdir ${wd}/tdb

for i in {001..014}
do
  mkdir -p ${wd}/tdb/hypothesis-${i}
  tdbloader2 --loc ${wd}/tdb/hypothesis-${i} --jvm-args -Xmx10g ${wd}/raw/hypothesis-${i}-raw.ttl
done
