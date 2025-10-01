VALID_VLENS = [64, 128, 256]
VALID_VLANE_WIDTHS = [32, 128, 512]

ML_INT = ["toycar_int8", "aww_int8"]
PROGRAMS_INT = ["cpptest"] + ML_INT
REQ_VECTOR_INT = ["basic_asm", "rvv_asm_bench"]

ML_FLOAT = []
PROGRAMS_FP = [] + ML_FLOAT
REQ_VECTOR_FP = []

# Change this to the array of tests you want to use
USE_TESTS = ["rvv_asm_bench"]
USE_VLENS = [64, 128, 256]
USE_VLANE_WIDTHS = [32]

CUSTOM_TARGETS = {
    "sanitycheck": [
        "basic_asm",
        "tests",
        "loadstores",
        "load_alu_vv_store",
        "load_alu_vx_store",
        "load_div_store",
        "load_macc_vv_store",
    ],
    "ml_bench": ["tflm_toy", "tflm_aww"],
    "simple_bench": ["rvv_asm_bench"],
}

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
        "build_ml_tests": False,
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

TIMEOUT = 200000
STOP_ON_ERROR = False
PRINT_STDERR = True
PRINT_BUILD_STDOUT = False
PRINT_TEST_STDOUT = False
