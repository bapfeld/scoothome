#!/bin/bash

python model_selection.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --changepoint_prior_scale=0.05 \
       --pdf_dir=/home/bapfeld/scoothome/figures/prophet_tuning/ &
python model_selection.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --changepoint_prior_scale=0.2 \
       --pdf_dir=/home/bapfeld/scoothome/figures/prophet_tuning/ &
python model_selection.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --changepoint_prior_scale=0.5 \
       --pdf_dir=/home/bapfeld/scoothome/figures/prophet_tuning/
