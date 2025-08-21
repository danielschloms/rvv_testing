VALID_VLENS = [64, 256, 1024]
VALID_VLANE_WIDTHS = [32, 128, 512]

ML_INT = ["toycar_int8", "aww_int8"]
PROGRAMS_INT = ["cpptest"] + ML_INT
REQ_VECTOR_INT = ["basic_asm", "rvv_asm_bench"]

ML_FLOAT = []
PROGRAMS_FP = [] + ML_FLOAT
REQ_VECTOR_FP = []

# Change this to the array of tests you want to use
USE_TESTS = ["toycar_int8"]
USE_VLENS = [64]
USE_VLANE_WIDTHS = [32]

TEST_CONFIG = {
    "rv32im_zicsr": {
        "abi": "ilp32",
        "vlens": USE_VLENS,
        "vlane_widths": USE_VLANE_WIDTHS,
        "targets": USE_TESTS,
        "build_scalar_tests": False,
        "build_vector_tests": True,
        "build_ml_tests": True,
        "skip": True,
    },
    "rv32im_zve32x": {
        "abi": "ilp32",
        "vlens": USE_VLENS,
        "vlane_widths": USE_VLANE_WIDTHS,
        "targets": USE_TESTS,
        "build_scalar_tests": False,
        "build_vector_tests": False,
        "build_ml_tests": True,
        "skip": False,
    },
    "rv32imf_zve32f": {
        "abi": "ilp32f",
        "vlens": USE_VLENS,
        "vlane_widths": USE_VLANE_WIDTHS,
        "targets": USE_TESTS,
        "build_scalar_tests": False,
        "build_vector_tests": True,
        "build_ml_tests": False,
        "skip": True,
    },
}

TIMEOUT = 200
STOP_ON_ERROR = False
PRINT_STDERR = True
PRINT_BUILD_STDOUT = False
PRINT_TEST_STDOUT = False
