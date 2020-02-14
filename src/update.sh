#!/bin/bash

# make sure we have latest version of code
git pull

# make sure directory structure is clean for update
rm -rf /tmp/scooter_records/ /tmp/bicycle_records
mkdir /tmp/scooter_records /tmp/bicycle_records

# Fetch new data and convert to time series
python update.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --num_proc=$(nproc)

# Calculate new scooter models
python estimate_models.py \
       --ini_path=~/scoothome/setup.ini \
       --vehicle_type='scooter' \
       --num_proc=$(nproc)

# Calculate new bike models
python estimate_models.py \
       --ini_path=~/scoothome/setup.ini \
       --vehicle_type='bicycle' \
       --num_proc=$(nproc)
