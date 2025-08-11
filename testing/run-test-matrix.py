#!/usr/bin/env python3

import os
import pathlib
import subprocess
import argparse
import config
from util import error, success, info, warn, check_path


WS_PATH_ENV_NAME = "WS_PATH"
WS_PATH_ENV = os.getenv(WS_PATH_ENV_NAME)
if not WS_PATH_ENV:
    print(f'Environment Variable "{WS_PATH_ENV_NAME}" not set')
    exit()

WS_PATH = pathlib.Path(WS_PATH_ENV)
PERFSIM_PRJ_SRC = WS_PATH / "gen_perfsim"
VERILATOR_PRJ_SRC = WS_PATH / "vicuna2_tinyml_benchmarking"
TEST_PRJ_SRC = WS_PATH / "riscv_programs"
check_path(WS_PATH)
check_path(VERILATOR_PRJ_SRC)
check_path(TEST_PRJ_SRC)
check_path(PERFSIM_PRJ_SRC)
print(f"Perfsim Project Source: {PERFSIM_PRJ_SRC}")
print(f"Verilator Project Source: {VERILATOR_PRJ_SRC}")
print(f"Test Project Source: {TEST_PRJ_SRC}")

VALID_VLENS = [64, 128, 256, 512, 1024]
VALID_ARCHS = ["rv32im_zve32x", "rv32imf_zve32f"]
ARCH_INFO = {
    "rv32im_zve32x": {"has_float": False},
    "rv32imf_zve32f": {"has_float": True},
}

VALID_VLANE_WIDTHS = [32, 64, 128, 256, 512]
VLANE_WIDHT_COMBINATIONS = {
    # VLEN : [legal VLANE_Ws]
    64: [32],
    128: [32, 64],
    256: [32, 64, 128],
    512: [32, 64, 128, 256],
    1024: [32, 64, 128, 256, 512],
}

SANITY_CHECK = ["basic_asm", "cpptest"]
PROGRAMS = ["toycar_int8"]


def build_rtl(arch: str, vlen: int, vlane_width: int, clean_rtl: bool) -> bool:
    fname = "build_rtl"
    info(
        fname,
        f"Building RTL model for arch {arch}, VLEN {vlen}, VLANE_WIDTH {vlane_width}",
    )
    if vlen not in VALID_VLENS:
        error(fname, f"Illegal VLEN {vlen}")
    if arch not in VALID_ARCHS:
        error(fname, f"Illegal ARCH {arch}")

    build_script_name = "build-rtl.sh"
    build_script = VERILATOR_PRJ_SRC / build_script_name
    build_args = [
        build_script,
        "vlen",
        str(vlen),
        "arch",
        arch,
        "vlane",
        str(vlane_width),
    ]
    proc = subprocess.run(args=build_args, capture_output=True, encoding="utf-8")
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"Process returned stderr{stderr_out}")
        return False
    success(fname, "Success")
    return True


def build_rtl_list(test_config: dict, clean_rtl: bool) -> bool:
    info("build_rtl_list", "Building RTL models")
    all_successful = True
    archs = test_config.keys()
    for arch in archs:
        vlens = test_config[arch]["vlens"]
        vlane_widths = test_config[arch]["vlane_widths"]
        for vlen in vlens:
            for vlane_width in vlane_widths:
                if vlane_width not in VLANE_WIDHT_COMBINATIONS[vlen]:
                    # Skip illegal VLEN / VLANE_W combinations
                    continue
                if not build_rtl(arch, vlen, vlane_width, clean_rtl):
                    all_successful = False

    return all_successful


def build_test(arch: str, vlen: int, build_ml_tests: bool, clean_tests: bool) -> bool:
    fname = "build_test"
    info(fname, f"Building RTL model for arch {arch}, VLEN {vlen}")
    if vlen not in VALID_VLENS:
        error(fname, f"Illegal VLEN {vlen}")
    if arch not in VALID_ARCHS:
        error(fname, f"Illegal ARCH {arch}")

    build_script_name = "etiss-build.sh"
    build_script = TEST_PRJ_SRC / build_script_name
    build_args = [
        build_script,
        "--vlen",
        str(vlen),
        "--arch",
        arch,
    ]

    if build_ml_tests:
        build_args.append("--ml")
    if clean_tests:
        build_args.append("--clean")

    proc = subprocess.run(args=build_args, capture_output=True, encoding="utf-8")
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"Process returned stderr{stderr_out}")
        if config.STOP_ON_ERROR:
            exit(1)
        return False
    success(fname, "Success")
    return True


def build_all_tests(test_config: dict, clean_tests: bool) -> bool:
    info("build_all_tests", "Building tests")
    all_successful = True
    archs = test_config.keys()
    for arch in archs:
        vlens = test_config[arch]["vlens"]
        build_ml_tests = test_config[arch]["build_ml_tests"]
        for vlen in vlens:
            if not build_test(arch, vlen, build_ml_tests, clean_tests):
                all_successful = False

    return all_successful


def run_test_etiss(arch: str, vlen: int, vlane_width: int, target: str) -> bool:
    fname = "run_test_etiss"
    info(fname, f"Running test {target} on {arch}_zvl{vlen}b")

    run_script_name = "run-target.sh"
    run_script_path = PERFSIM_PRJ_SRC / run_script_name

    run_args = [run_script_path, arch, str(vlen), str(vlane_width), target]
    proc = subprocess.run(args=run_args, capture_output=True, encoding="utf-8")
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"Process returned stderr{stderr_out}")
        if config.STOP_ON_ERROR:
            exit(1)
        return False
    success(fname, "Success")
    return True


def run_test_verilator(arch: str, vlen: int, vlane_width: int, target: str) -> bool:
    fname = "run_test_verilator"
    info(
        fname,
        f"Running test {target} on {arch}_zvl{vlen}b with VLANE_WITH {vlane_width}",
    )

    run_script_name = "run-target.sh"
    run_script_path = VERILATOR_PRJ_SRC / run_script_name

    run_args = [run_script_path, arch, str(vlen), str(vlane_width), target]
    proc = subprocess.run(args=run_args, capture_output=True, encoding="utf-8")
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"Process returned stderr{stderr_out}")
        if config.STOP_ON_ERROR:
            exit(1)
        return False
    success(fname, "Success")
    return True


def run_all(test_config: dict, run_etiss: bool, run_verilator: bool) -> None:
    info("run_all", f"Running tests for ETISS: {run_etiss}, Verilator: {run_verilator}")
    all_successful = True
    archs = test_config.keys()
    for arch in archs:
        vlens = test_config[arch]["vlens"]
        targets = test_config[arch]["targets"]
        vlane_widths = test_config[arch]["vlane_widths"]
        for vlen in vlens:
            for vlane_width in vlane_widths:
                for target in targets:
                    if run_etiss:
                        if not run_test_etiss(arch, vlen, vlane_width, target):
                            all_successful = False
                    if run_verilator:
                        if not run_test_verilator(arch, vlen, vlane_width, target):
                            all_successful = False

    return all_successful


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="TestMatrix",
        description="Builds RVV Verilator models & tests and runs them",
        epilog="TODO",
    )
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-r", "--build_rtl", action="store_true")
    parser.add_argument("-t", "--build_tests", action="store_true")
    # Clean RTL does nothing ATM
    parser.add_argument("-cr", "--clean_rtl", action="store_true")
    parser.add_argument("-ct", "--clean_tests", action="store_true")

    mutex_run_group = parser.add_mutually_exclusive_group(required=False)
    mutex_run_group.add_argument("-re", "--run_etiss", action="store_true")
    mutex_run_group.add_argument("-rv", "--run_verilator", action="store_true")

    args = parser.parse_args()

    run_etiss = True
    run_verilator = True

    if args.run_etiss:
        run_verilator = False
    elif args.run_verilator:
        run_etiss = False

    test_config = config.TEST_CONFIG
    if args.all:
        test_config = {
            arch: {"vlens": VALID_VLENS, "vlane_widths": VALID_VLANE_WIDTHS}
            for arch in VALID_ARCHS
        }

    if args.build_rtl:
        build_rtl_list(test_config, args.clean_rtl)

    if args.build_tests:
        build_all_tests(test_config, args.clean_tests)

    run_all(test_config, run_etiss, run_verilator)


if __name__ == "__main__":
    main()
