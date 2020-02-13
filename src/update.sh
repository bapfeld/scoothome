#!/bin/bash

# make sure we have latest version of code
git pull

python update.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini
