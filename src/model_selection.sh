#!/bin/bash

python model_selection.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --changepoint_prior_scale=0.05 \
       --pdf_out=/home/bapfeld/scoothome/figures/prophet_tuning/cpp05.pdf &
python model_selection.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --changepoint_prior_scale=0.1 \
       --pdf_out=/home/bapfeld/scoothome/figures/prophet_tuning/cpp1.pdf &
python model_selection.py \
       --ini_path=/home/bapfeld/scoothome/setup.ini \
       --changepoint_prior_scale=0.5 \
       --pdf_out=/home/bapfeld/scoothome/figures/prophet_tuning/cp5.pdf
