#!/bin/bash

PROJ_ROOT=/home/bapfeld/scoothome

python convert_to_ts.py \
       --dat_path=$PROJ_ROOT/data/Shared_Micromobility_Vehicle_Trips.csv \
       --vehicle_type='scooter' \
       --multi \
       --multi_out='/home/bapfeld/scoothome/data/device_records/'
