#!/usr/bin/env python3

import argparse
import multiprocessing as mp
import pathlib
import subprocess

import config
from util import check_path, error, info, success, warn
from fastcomparison import compare_fast


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

SRC_DIR = pathlib.Path(__file__).parent.resolve()
COMPARISON_PRJ_DIR = SRC_DIR.parent
PROJECT_ROOT_DIR = COMPARISON_PRJ_DIR.parent

PERFSIM_PRJ_SRC = PROJECT_ROOT_DIR / "Perfsim"
VERILATOR_PRJ_SRC = PROJECT_ROOT_DIR / "Vicuna2"
TEST_PRJ_SRC = PROJECT_ROOT_DIR / "RISCV_Programs"
COMPARISON_DIR = COMPARISON_PRJ_DIR / "comparison"
TABLE_DIR = COMPARISON_DIR / "table"
# RUNTIME_DIR = COMPARISON_DIR / "runtime"

check_path(PROJECT_ROOT_DIR)
check_path(VERILATOR_PRJ_SRC)
check_path(TEST_PRJ_SRC)
check_path(PERFSIM_PRJ_SRC)
# check_path(RUNTIME_DIR)
info(__name__, f"Perfsim Project Source: {PERFSIM_PRJ_SRC}")
info(__name__, f"Verilator Project Source: {VERILATOR_PRJ_SRC}")
info(__name__, f"Test Project Source: {TEST_PRJ_SRC}")
info(__name__, f"Table Directory: {TABLE_DIR}")
# info(__name__, f"Runtime Directory: {RUNTIME_DIR}")

VALID_VLENS = [64, 128, 256, 512, 1024]
VALID_ARCHS = ["rv32im_zicsr", "rv32im_zve32x", "rv32imf_zve32f"]

VALID_VLANE_WIDTHS = [32, 64, 128, 256, 512]
VLANE_WIDTH_COMBINATIONS = {
    # VLEN : [legal VLANE_Ws]
    64: [32],
    128: [32, 64],
    256: [32, 64, 128],
    512: [32, 64, 128, 256],
    1024: [32, 64, 128, 256, 512],
}

def build_rtl(arch: str, vlen: int, vlane_width: int, optargs: list[str]) -> bool:
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
        "--vlen",
        str(vlen),
        "--arch",
        arch,
        "--vlane_width",
        str(vlane_width),
    ]

    build_args += optargs

    proc = subprocess.run(args=build_args, capture_output=True, encoding="utf-8")
    if proc.stderr:
        stderr_out = f"\n{proc.stderr}" if config.PRINT_STDERR else ""
        error(fname, f"Process returned stderr{stderr_out}")
        return False
    success(fname, "Success")
    return True


def build_rtl_list(test_config: dict, optargs: list[str]) -> bool:
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
                if not build_rtl(arch, vlen, vlane_width, optargs):
                    all_successful = False

    return all_successful


def build_test(
    arch: str,
    abi: str,
    vlen: int,
    build_type: BuildType,
    compiler: str,
    target: str,
    optargs: list[str],
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

    build_script_name = "build.sh"
    build_script = TEST_PRJ_SRC / build_script_name
    build_args = [
        build_script,
        "--arch",
        arch,
        "--abi",
        abi,
        "--vlen",
        str(vlen),
        "--compiler",
        compiler,
        "--target",
        target,
    ]

    build_args += optargs

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
    test_config: dict,
    build_type: BuildType,
    compiler: str,
    build_target: str,
    optargs: list[str],
) -> bool:
    info("build_all_tests", "Building tests")
    all_successful = True
    archs = test_config.keys()
    for arch in archs:
        abi = test_config[arch]["abi"]
        if test_config[arch]["skip"]:
            continue
        vlens = test_config[arch]["vlens"]
        for vlen in vlens:
            all_successful &= build_test(
                arch, abi, vlen, build_type, compiler, build_target, optargs
            )

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

    run_args = [
        run_script_path,
        "--arch",
        arch,
        "--vlen",
        str(vlen),
        "--vlane_width",
        str(vlane_width),
        "--target",
        target,
    ]
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

    # stdout_lines = proc.stdout.split("\n")
    # time: str = ""
    # for line in stdout_lines:
    #     if "user" in line:
    #         time = line.strip().split(" ")[1]
    #         with open(RUNTIME_DIR / target, "a", encoding="utf-8") as runtime_file:
    #             runtime_file.write(f"{vlen} & {vlane_width} & {time}\n")
    #         break

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
    test_config: dict,
    run_etiss: bool,
    run_verilator: bool,
    n_processes: int = 1,
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


def compare_all(argslist: list[tuple[str, int, int, str]], gen_table: bool) -> bool:
    ok = True
    results = []
    fname = "compare_all"

    for args in argslist:
        arch, vlen, vlane_width, target = args
        # Returns CPI ETISS, CPI Verilator, CPI Error in %, Abs sum of differences, OK
        info(
            fname,
            f"Compare {target} on {arch} with VLEN {vlen} and VLANE_WIDTH {vlane_width}",
        )
        cpi_e, cpi_v, cpi_error, abs_sum_diffs, n_instructions, ok_run = compare_fast(
            arch,
            vlen,
            vlane_width,
            target,
            keep_traces=False,
            print_stages=True,
            write_match=True,
        )
        if ok_run:
            success(
                fname,
                f"Comparison results: CPI ETISS {cpi_e:.4f} | CPI RTL {cpi_v:.4f} | Error {cpi_error:.4f}% | ASD {abs_sum_diffs} | ADI {abs_sum_diffs / n_instructions:.4f}",
            )
        else:
            error(fname, "Comparison failed")
        if "_" in target:
            target = target.replace("_", "\\_")
        if "_" in arch:
            arch = arch.replace("_", "\\_")
        avg_diff_per_instruction = abs_sum_diffs / n_instructions
        results.append(
            (
                target,
                arch,
                vlen,
                vlane_width,
                cpi_e,
                cpi_v,
                cpi_error,
                avg_diff_per_instruction,
                n_instructions,
            )
        )
        ok &= ok_run

    if gen_table:
        info(fname, "Generate table")
        with open(TABLE_DIR / "table.tex", "w", encoding="utf-8") as table_file:
            table_file.write("\\begin{center}\n")
            table_file.write("\\begin{tabular}{ c c c c c c c }\n")
            table_file.write(
                "Target & VLEN & VLANE\\_WIDTH & CPI ETISS & CPI Verilator & Error & ADI & # Instrs."
            )
            for result in results:
                (
                    r_target,
                    r_arch,
                    r_vlen,
                    r_vlane_width,
                    r_cpi_e,
                    r_cpi_v,
                    r_error,
                    r_avg_diff_per_inst,
                    r_n_instructrions,
                ) = result
                table_file.write(
                    f" \\\\\n{r_target} & {r_vlen} & {r_vlane_width} & {r_cpi_e:.4f} & {r_cpi_v:.4f} & {r_error:.4f} \\% & {r_avg_diff_per_inst:.4f} & {r_n_instructrions}"
                )
            table_file.write("\n\\end{tabular}\n\\end{center}\n")

    return ok


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


def test_sequential(test_config: dict):
    fname = "test_sequential"
    arglist = gen_argslist(test_config)
    ok = True
    with open(TABLE_DIR / "table_seq.txt", "w", encoding="utf-8") as seq_table:
        for args in arglist:
            arch, vlen, vlane_width, target = args
            pair = [
                [arch, vlen, vlane_width, target, "etiss"],
                [arch, vlen, vlane_width, target, "verilator"],
            ]
            with mp.Pool(processes=2) as pool:
                res = pool.starmap(run_test, pair)
                ok = False if False in res else True

            info(fname, f"Compare pair {arch}, {vlen}, {vlane_width}, {target}")
            cpi_e, cpi_v, cpi_error, abs_sum_diffs, n_instructions, ok_run = (
                compare_fast(
                    arch,
                    vlen,
                    vlane_width,
                    target,
                    keep_traces=False,
                    print_stages=False,
                    write_match=False,
                )
            )
            avg_diff_per_instr = abs_sum_diffs / n_instructions
            info(
                fname,
                f"{vlen} & {vlane_width} & {cpi_e:.4f} & {cpi_v:.4f} & {cpi_error:.4f} % & {avg_diff_per_instr:.4f} & {n_instructions}\n",
            )
            seq_table.write(
                f"{vlen} & {vlane_width} & {cpi_e:.4f} & {cpi_v:.4f} & {cpi_error:.4f} % & {avg_diff_per_instr:.4f} & {n_instructions}\n"
            )


def main() -> None:
    fname = "TestMatrix"
    parser = argparse.ArgumentParser(
        prog=fname,
        description="Builds RVV Verilator models & tests and runs them",
        epilog="TODO",
    )

    parser.add_argument("-r", "--build_rtl", action="store_true")
    parser.add_argument("-t", "--build_tests", action="store_true")
    parser.add_argument("-gt", "--generate_table", action="store_true")
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
    parser.add_argument("--trace", action="store_true")

    mutex_target_group = parser.add_mutually_exclusive_group(required=True)
    # CMake custom build target
    mutex_target_group.add_argument("--ctarget", type=str)
    # Actual program
    mutex_target_group.add_argument("--target", type=str)

    parser.add_argument("--keep_traces", action="store_true")
    parser.add_argument("--seq", action="store_true")

    args = parser.parse_args()

    run_etiss = False
    run_verilator = False

    if args.run_etiss or args.run_both:
        run_etiss = True
    if args.run_verilator or args.run_both:
        run_verilator = True

    build_target = "all"
    optargs_build = []
    optargs_rtl = []

    # Build optional arguments
    if args.clean_tests:
        optargs_build.append("--clean")

    # Verilator build optional arguments
    if args.trace:
        optargs_rtl.append("--trace")
    if args.clean_rtl:
        optargs_rtl.append("--clean")

    test_config = config.TEST_CONFIG

    if args.ctarget:
        for arch in test_config.values():
            arch["targets"] = config.CUSTOM_TARGETS[args.ctarget]
        build_target = args.ctarget

    if args.target:
        for arch in test_config.values():
            arch["targets"] = [args.target]
        build_target = args.target

    argslist = gen_argslist(test_config)

    if args.build_rtl:
        build_rtl_list(test_config, optargs_rtl)

    if args.build_tests:
        build_type = BuildType.release
        compiler = "llvm"
        if args.compiler:
            compiler = args.compiler
        if args.reldeb:
            build_type = BuildType.reldeb
        if args.debug:
            build_type = BuildType.debug
        build_all_tests(
            test_config, BuildType(build_type), compiler, build_target, optargs_build
        )

    if args.seq:
        test_sequential(test_config)
    else:
        if run_etiss or run_verilator:
            if run_all(test_config, run_etiss, run_verilator, 31):
                success(fname, "All tests passed")
            else:
                warn(fname, "Warning: Failing tests")

        if args.compare:
            if compare_all(argslist, args.generate_table):
                success(fname, "All comparisons correct")
            else:
                warn(fname, "Warning: comparison errors")

    if args.clean_output:
        clean_script_path = pathlib.Path(__file__).parent / "clean-output.sh"
        subprocess.run(clean_script_path)


if __name__ == "__main__":
    main()
