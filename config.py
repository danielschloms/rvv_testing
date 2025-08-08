TESTS_INT = ["toycar_int8"]
SANITY_INT = ["cpptest", "basic_asm"]
ALL_INT = TESTS_INT + SANITY_INT

TESTS_FLOAT = []
SANITY_FLOAT = []
ALL_FLOAT = TESTS_FLOAT + SANITY_FLOAT

ALL_TESTS = ALL_INT + ALL_FLOAT

RUN_INT = ["toycar_int8"]
RUN_FLOAT = []
RUN_ALL = RUN_INT + RUN_FLOAT

TEST_CONFIG = {
    "rv32im_zve32x": {"vlens": [64, 128, 256, 512, 1024], "vlane_widths": [32]}
}
