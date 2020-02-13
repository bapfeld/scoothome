#!/bin/bash

python estimate_models.py \
       --ini_path=~/scoothome/setup.ini \
       --vehicle_type='scooter' \
       --proc_num=$(nproc)

python estimate_models.py \
       --ini_path=~/scoothome/setup.ini \
       --vehicle_type='bicycle' \
       --proc_num=$(nproc)
