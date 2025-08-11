ML_TESTS_INT = ["toycar_int8", "aww_int8"]
TESTS_INT = ["rvvbench", "rvv_asm_bench", "vector_add"]
SANITY_INT = ["cpptest", "basic_asm"]
ALL_INT = TESTS_INT + SANITY_INT

TESTS_FLOAT = []
SANITY_FLOAT = []
ALL_FLOAT = TESTS_FLOAT + SANITY_FLOAT

ALL_TESTS = ALL_INT + ALL_FLOAT

RUN_INT = ML_TESTS_INT
RUN_FLOAT = []

# Change this to the array of tests you want to use
USE_TESTS = SANITY_INT

TEST_CONFIG = {
    "rv32im_zve32x": {
        "vlens": [64],
        "vlane_widths": [32],
        "targets": USE_TESTS,
        "build_scalar_tests": False,
        "build_vector_tests": False,
        "build_ml_tests": False,
    }
}

STOP_ON_ERROR = True
PRINT_STDERR = True
