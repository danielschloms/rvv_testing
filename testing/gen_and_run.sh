#!/usr/bin/bash

$WS_PATH/gen_perfsim/gen_vicuna.sh
$WS_PATH/rvv_testing/testing/run-test-matrix.py $*