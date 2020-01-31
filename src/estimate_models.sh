#!/bin/bash

python estimate_models.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --area_list_file=/home/bapfeld/scoothome/data/new_area_list.txt \
       --vehicle_type='scooter' \
       --completed_area_file=/home/bapfeld/scoothome/data/complete_model_list_1.txt \
       --proc_num=1 \
       --total_processes=3 &

python estimate_models.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --area_list_file=/home/bapfeld/scoothome/data/new_area_list.txt \
       --vehicle_type='scooter' \
       --completed_area_file=/home/bapfeld/scoothome/data/complete_model_list_2.txt \
       --proc_num=2 \
       --total_processes=3 &

python estimate_models.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --area_list_file=/home/bapfeld/scoothome/data/new_area_list.txt \
       --vehicle_type='scooter' \
       --completed_area_file=/home/bapfeld/scoothome/data/complete_model_list_3.txt \
       --proc_num=3 \
       --total_processes=3
       
