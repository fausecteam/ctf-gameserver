#!/bin/bash

terraform -chdir=$1 destroy -auto-approve
rm -r $1/output 2>&1
