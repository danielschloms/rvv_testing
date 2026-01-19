cd $WS_PATH/rvv_testing/testing

if [[ "$1" = "--trace" ]]; then
    echo "Build with trace"
    ./run-test-matrix.py -r --trace
else
    echo "Build without trace"
    ./run-test-matrix.py -r
fi