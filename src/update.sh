#!/bin/bash

# make sure we have latest version of code
git pull

# make sure directory structure is clean for update
rm -rf /tmp/scooter_records/ /tmp/bicycle_records
mkdir /tmp/scooter_records /tmp/bicycle_records

python update.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini
