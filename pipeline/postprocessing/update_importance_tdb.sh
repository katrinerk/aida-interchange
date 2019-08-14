#!/usr/bin/env bash

wd=$1

for i in {001..014}
do
  echo "Updating hypothesis-${i}"
  for f in `ls ${wd}/update_importance | grep hypothesis-${i}`
  do
    tdbupdate --loc ${wd}/tdb/hypothesis-${i} --update ${wd}/update_importance/${f}
  done &
done

wait
