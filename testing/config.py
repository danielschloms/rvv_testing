ML_INT = ["toycar_int8", "aww_int8"]
PROGRAMS_INT = ["cpptest"] + ML_INT
REQ_VECTOR_INT = ["basic_asm", "rvv_asm_bench"]

ML_FLOAT = []
PROGRAMS_FP = [] + ML_FLOAT
REQ_VECTOR_FP = []

# Change this to the array of tests you want to use
USE_VLENS = [64, 256, 1024]
USE_VLANE_WIDTHS = [32, 64]
# USE_VMEM_WIDTHS = [32, 64]

SANITYCHECK_TESTS = [
    "load_alu_vv_store",
    "load_mul_vv_store",
    "load_div_vv_store",
    "load_red_store",
    "load_store",
    "vmv_v_i_store",
]

ML_BENCH_TESTS = ["tflm_toy", "tflm_aww", "tflm_vww"]

CUSTOM_TARGETS = {
    "sanitycheck": SANITYCHECK_TESTS,
    "ml_bench": ML_BENCH_TESTS,
}

TEST_CONFIG = {
    "rv32im_zicsr": {
        "abi": "ilp32",
        "vlens": USE_VLENS,
        "vlane_widths": USE_VLANE_WIDTHS,
        # "vmem_widths": USE_VMEM_WIDTHS,
        "targets": [],
        "skip": True,
    },
    "rv32im_zve32x": {
        "abi": "ilp32",
        "vlens": USE_VLENS,
        "vlane_widths": USE_VLANE_WIDTHS,
        # "vmem_widths": USE_VMEM_WIDTHS,
        "targets": [],
        "skip": False,
    },
    "rv32imf_zve32f": {
        "abi": "ilp32f",
        "vlens": USE_VLENS,
        "vlane_widths": USE_VLANE_WIDTHS,
        # "vmem_widths": USE_VMEM_WIDTHS,
        "targets": [],
        "skip": True,
    },
}

TIMEOUT = 200000
STOP_ON_ERROR = False
PRINT_STDERR = True
PRINT_BUILD_STDOUT = True
PRINT_TEST_STDOUT = False
