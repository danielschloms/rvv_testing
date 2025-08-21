#!/usr/bin/bash

for arg in "$@"; do
    if [[ "$arg" = "-m" ]]; then
        rm -rf $WS_PATH/rvv_testing/comparison/match/*
    fi

    if [[ "$arg" = "-b" ]]; then
        rm -rf $WS_PATH/gen_perfsim/target_sw/examples/Vicuna/custom/*
        rm -rf $WS_PATH/vicuna2_tinyml_benchmarking/build_from_other/*
    fi
done

rm -rf $WS_PATH/rvv_testing/comparison/etiss/*
rm -rf $WS_PATH/rvv_testing/comparison/verilator/*
rm -rf $WS_PATH/gen_perfsim/out/*