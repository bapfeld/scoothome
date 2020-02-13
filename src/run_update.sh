#!/bin/bash

AMI=''
INSTANCE=''
SCRATCH=$(mktemp -d -t tmp.XXXXXXXXXX)
# Define a trap function to make sure we shut down even in the event of failure
function finish {
    if [ -n "$INSTANCE" ]; then
        ec2-terminate-instances "$INSTANCE"
    fi
    rm -rf "$SCRATCH"
}
trap finish EXIT

ec2-run-instances "$AMI" > "$SCRATCH/run-instance"
# Now extract the instance ID.
INSTANCE=$(grep '^INSTANCE' "$SCRATCH/run-instance" | cut -f 2)


