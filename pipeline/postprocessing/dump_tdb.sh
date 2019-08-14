#!/usr/bin/env bash

wd=$1
run_id=$2
soin_id=$3

mkdir ${wd}/final

for i in {001..014}
do
  output_path=${wd}/final/${run_id}.${soin_id}.${soin_id}_F1.H${i}.ttl
  echo "Dumping hypothesis-${i} to ${output_path}"
  tdbdump --formatted trig --loc ${wd}/tdb/hypothesis-${i} > ${output_path}
done
