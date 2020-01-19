#!/bin/bash

PROJ_ROOT=/home/bapfeld/scoothome

python convert_to_ts.py \
       --dat_path=$PROJ_ROOT/data/Shared_Micromobility_Vehicle_Trips.csv \
       --dat_out=$PROJ_ROOT/data/time_series.csv
