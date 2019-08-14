#!/usr/bin/env bash

wd=$1

for i in {001..014}
do
  echo "Updating hypothesis-${i}"
  tdbupdate --loc ${wd}/tdb/hypothesis-${i} --update ${wd}/update_handle/hypothesis-${i}-update.rq
done

wait
