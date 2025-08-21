#!/usr/bin/env python3

import argparse
import multiprocessing as mp
import os
import pathlib
import subprocess

import config
from util import check_path, error, info, success, warn

from comparison import compare


class BuildType(str):
    release = ""
    debug = "--debug"
    reldeb = "--reldeb"


ETISS_SUCCESS_STRING = "Success"
ETISS_FAIL_STRING = "Fail"
ETISS_ERROR_STRING = "ETISS: Error"

VERILATOR_SUCCESS_STRING = "Output Match"
VERILATOR_FAIL_STRING = "Output Mismatch"
VERILATOR_INTERRUPT_STRING = "Interrupt Called"

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
    "rv32im_zicsr": {
        "abi": "ilp32",
        "scalar_only": True,
        "has_vector_int": False,
        "has_scalar_float": False,
        "has_vector_float": False,
    },
    "rv32im_zve32x": {
        "abi": "ilp32",
        "scalar_only": False,
        "has_vector_int": True,
        "has_scalar_float": False,
        "has_vector_float": False,
    },
    "rv32imf_zve32f": {
        "abi": "ilp32f",
        "scalar_only": False,
        "has_vector_int": True,
        "has_scalar_float": True,
        "has_vector_float": True,
    },
}

VALID_VLANE_WIDTHS = [32, 64, 128, 256, 512]
VLANE_WIDTH_COMBINATIONS = {
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
        if test_config[arch]["skip"]:
            continue
        vlens = test_config[arch]["vlens"]
        vlane_widths = test_config[arch]["vlane_widths"]
        for vlen in vlens:
            for vlane_width in vlane_widths:
                if vlane_width not in VLANE_WIDTH_COMBINATIONS[vlen]:
                    # Skip illegal VLEN / VLANE_W combinations
                    continue
                if not build_rtl(arch, vlen, vlane_width, clean_rtl):
                    all_successful = False

    return all_successful


def build_test(
    arch: str,
    abi: str,
    vlen: int,
    build_ml_tests: bool,
    build_vector_tests: bool,
    clean_tests: bool,
    build_type: BuildType,
    compiler: str = "gcc",
) -> bool:
    fname = "build_test"
    info(
        fname,
        f"Building tests for {arch}, VLEN {vlen} with {compiler.upper()}, {build_type if build_type != "" else "release"}",
    )
    if vlen not in VALID_VLENS:
        error(fname, f"Illegal VLEN {vlen}")
    if arch not in VALID_ARCHS:
        error(fname, f"Illegal ARCH {arch}")
    if compiler not in ["gcc", "llvm"]:
        error(fname, f"Invalid compiler {compiler}")

    build_script_name = "etiss-build.sh"
    build_script = TEST_PRJ_SRC / build_script_name
    build_args = [
        build_script,
        "--arch",
        arch,
        "--abi",
        abi,
        "--vlen",
        str(vlen),
        f"--{compiler}",
    ]

    if build_ml_tests:
        build_args.append("--ml")
    if build_vector_tests:
        build_args.append("--vector")
    if clean_tests:
        build_args.append("--clean")

    if build_type != BuildType.release:
        build_args.append(build_type)

    proc = subprocess.run(args=build_args, capture_output=True, encoding="utf-8")
    if config.PRINT_BUILD_STDOUT and proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"Process returned stderr{stderr_out}")
        if config.STOP_ON_ERROR:
            exit(1)
        return False

    success(fname, "Success")
    return True


def build_all_tests(
    test_config: dict, clean_tests: bool, build_type: BuildType, compiler: str = "gcc"
) -> bool:
    info("build_all_tests", "Building tests")
    all_successful = True
    archs = test_config.keys()
    for arch in archs:
        abi = test_config[arch]["abi"]
        if test_config[arch]["skip"]:
            continue
        vlens = test_config[arch]["vlens"]
        build_ml_tests = test_config[arch]["build_ml_tests"]
        build_vector_tests = test_config[arch]["build_vector_tests"]
        for vlen in vlens:
            if not build_test(
                arch,
                abi,
                vlen,
                build_ml_tests,
                build_vector_tests,
                clean_tests,
                build_type,
                compiler,
            ):
                all_successful = False

    return all_successful


def run_test(
    arch: str, vlen: int, vlane_width: int, target: str, simulator: str
) -> bool:
    if simulator not in ["etiss", "verilator"]:
        error("run_test", f"Invalid simulator {simulator}")
    fname = f"run_test, {simulator}"
    full_arch_string = f"{arch}_zvl{vlen}b, VLANE_WIDTH {vlane_width}"
    target_sw_width = 15
    error_msg_header = f"\tError {target:{target_sw_width + 2}} on {full_arch_string}"
    info(fname, f"\tRunning {target:{target_sw_width}} on {full_arch_string}")

    run_script_name = "run-target.sh"
    run_script_dir = PERFSIM_PRJ_SRC if simulator == "etiss" else VERILATOR_PRJ_SRC
    run_script_path = run_script_dir / run_script_name

    run_args = [run_script_path, arch, str(vlen), str(vlane_width), target]
    try:
        proc = subprocess.run(
            args=run_args,
            capture_output=True,
            encoding="utf-8",
            timeout=config.TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        error(fname, f"{error_msg_header} Process timed out")
        return False

    if config.PRINT_TEST_STDOUT and proc.stdout:
        print(proc.stdout)
    # Check for error
    # TODO: Be able to abort all processes on error?
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"{error_msg_header} Process returned stderr{stderr_out}")
        if config.STOP_ON_ERROR:
            exit(1)
        return False

    # Check output for fail/success
    success_found = False
    if simulator == "etiss":
        if ETISS_FAIL_STRING in proc.stdout:
            error(fname, f"{error_msg_header}: Fail (By program report)")
            return False
        if ETISS_ERROR_STRING in proc.stdout:
            error(fname, f"{error_msg_header}: Fail (ETISS error)")
            return False
        if ETISS_SUCCESS_STRING in proc.stdout:
            success_found = True
    else:
        if VERILATOR_FAIL_STRING in proc.stdout:
            error(fname, f"{error_msg_header}: Fail (Output Mismatch)")
            return False
        if VERILATOR_INTERRUPT_STRING in proc.stdout:
            error(fname, f"{error_msg_header}: Fail (Interrupt Called)")
            return False
        if VERILATOR_SUCCESS_STRING in proc.stdout:
            success_found = True

    success(
        fname,
        (
            f"\tSuccess {target:{target_sw_width}} on {full_arch_string}"
            + (": Success string found" if success_found else "")
        ),
    )
    return True


def run_all(
    test_config: dict, run_etiss: bool, run_verilator: bool, n_processes: int
) -> bool:
    fname = "run_all"
    info(fname, f"Running tests for ETISS: {run_etiss}, Verilator: {run_verilator}")
    archs = test_config.keys()
    arglist = []

    for arch in archs:
        if test_config[arch]["skip"]:
            continue
        vlens = test_config[arch]["vlens"]
        targets = test_config[arch]["targets"]
        vlane_widths = test_config[arch]["vlane_widths"]
        for vlen in vlens:
            for vlane_width in vlane_widths:
                if vlane_width not in VLANE_WIDTH_COMBINATIONS[vlen]:
                    # Skip illegal VLEN / VLANE_W combinations
                    continue
                for target in targets:
                    if run_etiss:
                        arglist.append((arch, vlen, vlane_width, target, "etiss"))
                    if run_verilator:
                        arglist.append((arch, vlen, vlane_width, target, "verilator"))

    if n_processes > mp.cpu_count():
        info(fname, f"# of processes higher than nproc, reducing to {mp.cpu_count()}")
    with mp.Pool(processes=n_processes) as pool:
        res = pool.starmap(run_test, arglist)

    return False if False in res else True


def run_comparison(
    arch: str, vlen: int, vlane_width: int, target: str
) -> tuple[bool, float]:
    compare(arch, vlen, vlane_width, target)
    return (False, 1.0)


def compare_all(argslist: list[tuple[str, int, int, str]]) -> bool:
    for args in argslist:
        arch, vlen, vlane_width, target = args
        run_comparison(arch, vlen, vlane_width, target)
    return True


def gen_argslist(test_config: dict) -> list[tuple[str, int, int, str]]:
    archs = test_config.keys()
    argslist: list[tuple[str, int, int, str]] = []
    for arch in archs:
        if test_config[arch]["skip"]:
            continue
        vlens = test_config[arch]["vlens"]
        targets = test_config[arch]["targets"]
        vlane_widths = test_config[arch]["vlane_widths"]
        for vlen in vlens:
            for vlane_width in vlane_widths:
                if vlane_width not in VLANE_WIDTH_COMBINATIONS[vlen]:
                    # Skip illegal VLEN / VLANE_W combinations
                    continue
                for target in targets:
                    argslist.append((arch, vlen, vlane_width, target))

    return argslist


def main() -> None:
    fname = "TestMatrix"
    parser = argparse.ArgumentParser(
        prog=fname,
        description="Builds RVV Verilator models & tests and runs them",
        epilog="TODO",
    )
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-r", "--build_rtl", action="store_true")
    parser.add_argument("-t", "--build_tests", action="store_true")
    parser.add_argument("-cmp", "--compare", action="store_true")
    # parser.add_argument("-j") # TODO: specify number of processes
    # Clean RTL does nothing ATM
    parser.add_argument("-cr", "--clean_rtl", action="store_true")
    parser.add_argument("-ct", "--clean_tests", action="store_true")
    parser.add_argument("-co", "--clean_output", action="store_true")

    mutex_run_group = parser.add_mutually_exclusive_group(required=False)
    mutex_run_group.add_argument("-re", "--run_etiss", action="store_true")
    mutex_run_group.add_argument("-rv", "--run_verilator", action="store_true")
    mutex_run_group.add_argument("-rb", "--run_both", action="store_true")

    mutex_build_type_group = parser.add_mutually_exclusive_group(required=False)
    mutex_build_type_group.add_argument("-d", "--debug", action="store_true")
    mutex_build_type_group.add_argument("-reldeb", "--reldeb", action="store_true")

    parser.add_argument("--compiler", type=str, required=False)

    args = parser.parse_args()

    run_etiss = False
    run_verilator = False

    if args.run_etiss or args.run_both:
        run_etiss = True
    elif args.run_verilator or args.run_both:
        run_verilator = True

    test_config = config.TEST_CONFIG
    if args.all:
        test_config = {
            arch: {
                "abi": ARCH_INFO[arch]["abi"],
                "vlens": VALID_VLENS,
                "vlane_widths": VALID_VLANE_WIDTHS,
                "targets": config.PROGRAMS_INT
                + (config.REQ_VECTOR_INT if ARCH_INFO[arch]["has_vector_int"] else [])
                + (config.PROGRAMS_FP if ARCH_INFO[arch]["has_scalar_float"] else [])
                + (config.REQ_VECTOR_FP if ARCH_INFO[arch]["has_vector_float"] else []),
                "build_scalar_tests": True,  # TODO
                "build_vector_tests": True,
                "build_ml_tests": True,
                "skip": False,
            }
            for arch in VALID_ARCHS
        }

    argslist = gen_argslist(test_config)

    if args.build_rtl:
        build_rtl_list(test_config, args.clean_rtl)

    if args.build_tests:
        build_type = BuildType.release
        compiler = "llvm"
        if args.compiler:
            compiler = args.compiler
        if args.reldeb:
            build_type = BuildType.reldeb
        if args.debug:
            build_type = BuildType.debug
        build_all_tests(test_config, args.clean_tests, BuildType(build_type), compiler)

    if run_etiss or run_verilator:
        if run_all(test_config, run_etiss, run_verilator, 16):
            success(fname, "All tests passed")
        else:
            warn(fname, "Warning: Failing tests")

    if args.compare:
        if compare_all(argslist):
            success(fname, "All comparisons correct")
        else:
            warn(fname, "Warning: comparison errors")

    if args.clean_output:
        clean_script_path = pathlib.Path(__file__).parent / "clean-output.sh"
        subprocess.run(clean_script_path)


if __name__ == "__main__":
    main()
