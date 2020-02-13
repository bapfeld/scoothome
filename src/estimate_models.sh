#!/bin/bash

for i in $(seq 1 $1)
do
    if [ $i != $1 ]
    then
        python estimate_models.py \
               --ini_path=~/scoothome/setup.ini \
               --area_list_file=~/scoothome/data/new_area_list.txt \
               --vehicle_type='scooter' \
               --completed_area_file=~/scoothome/data/complete_model_list_$i.txt \
               --proc_num=$i \
               --total_processes=$1 &
    else
        python estimate_models.py \
               --ini_path=~/scoothome/setup.ini \
               --area_list_file=~/scoothome/data/new_area_list.txt \
               --vehicle_type='scooter' \
               --completed_area_file=~/scoothome/data/complete_model_list_$i.txt \
               --proc_num=$i \
               --total_processes=$1
    fi
done
