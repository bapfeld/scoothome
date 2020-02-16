#!/bin/bash

# make sure we're in the correct directory
cd ~/scoothome

# make sure we have latest version of code
git pull

# activate our environment
workon scoothome

# make sure directory structure is clean for update
rm -rf /tmp/scooter_records/ /tmp/bicycle_records
mkdir /tmp/scooter_records /tmp/bicycle_records

# move into the src directory
cd src

# Fetch new data and convert to time series
python update.py \
       --ini_path=~/scoothome/setup.ini \
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

if [ $(whoami) == 'ubuntu' ]
then
    sudo shutdown -h now
fi
