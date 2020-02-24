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
echo 'Updating time series at $(date +"%T")'
python update.py \
       --ini_path=~/scoothome/setup.ini \
       --num_proc=$(nproc)

# Calculate new scooter models
echo 'Running scooter models update at $(date +"%T")'
python estimate_models.py \
       --ini_path=~/scoothome/setup.ini \
       --vehicle_type='scooter' \
       --num_proc=$(nproc)

# Calculate new bike models
echo 'Running bicycle models update at $(date +"%T")'
python estimate_models.py \
       --ini_path=~/scoothome/setup.ini \
       --vehicle_type='bicycle' \
       --num_proc=$(nproc)

# Drop old predictions
echo 'Dropping old predictions at $(date +"%T")'
python drop_old_predictions.py \
       --ini_path=~/scoothome/setup.ini

if [ $USER == 'ubuntu' ]
then
    sudo shutdown -h now
fi
