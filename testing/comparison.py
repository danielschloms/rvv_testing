#!/usr/bin/env python3

import csv
import os
import pathlib
import re
import sys
from difflib import SequenceMatcher

import decoder
import numpy as np
from timingconfig import V_SHORT_SIGNAL, V_LONG_SIGNAL
from util import blue, bold, check_path

ARCH: str
VLEN: int
VLANE_WIDTH: int
TARGET_SW: str

TRANSFORM_TRACES = False
VERBOSE = False

COMPARISON_DIR = pathlib.Path(__file__).parent.parent / "comparison"
check_path(COMPARISON_DIR)

# vset(i)vl(i) retires after ID
VSET_INSTRS = ["vsetvl", "vsetvli", "vsetivli"]

DELTA_TRESHOLD = 10
VSET_TIMING_STAGE = "EX_stage"
FAST_TIMING_STAGE = "EX_stage"
# SLOW_TIMING_STAGE = "V_EX_LSU_ELM_Pack_substage"
SLOW_TIMING_STAGE = "EX_stage"
SCALAR_TIMING_STAGE = "EX_stage"

TRACK_STAGES = [
    "IF_stage",
    "ID_stage",
    "EX_stage",
    "WB_stage",
    "V_ID_stage",
    "V_IQ_stage",
    "V_DISP_stage",
    "V_EX_LSU_ELM_Pack_substage",
    # "V_EX_stage",
    "V_RES_stage",
    # "V_CFG_stage",
]

PRINT_STAGES = [
    "IF_stage",
    "ID_stage",
    "EX_stage",
    "WB_stage",
    "V_ID_stage",
    "V_IQ_stage",
    "V_DISP_stage",
    "V_EX_LSU_ELM_Pack_substage",
    # "V_EX_stage",
    "V_RES_stage",
    # "V_CFG_stage",
]

MAX_STAGE_NAME_LEN = len(max(PRINT_STAGES, key=len))
START_LABEL = "address_match_start"
END_LABEL = "address_match_end"

STAGE_IN_COL = True


def print_info(msg: str):
    if VERBOSE:
        print(msg)


def read_addresses(
    target_sw: str, verilator_dump_dir: pathlib.Path, etiss_dump_dir: pathlib.Path
) -> dict:
    """Returns a dictionary with start and end addresses."""
    verilator_start = 0
    verilator_end = 0
    etiss_start = 0
    etiss_end = 0

    verilator_dump_file = f"{verilator_dump_dir}/{target_sw}_dump.txt"
    try:
        with open(verilator_dump_file, "r", encoding="utf-8") as verilator_dump:
            for line in verilator_dump:
                if f"<{START_LABEL}>:" in line:
                    verilator_start = int(line.split(" ")[0], 16)
                if f"<{END_LABEL}>:" in line:
                    verilator_end = int(line.split(" ")[0], 16)
    except:
        print_info(f"(AddressMatcher) Could not find {target_sw} Verilator dump")
        pass

    etiss_dump_file = f"{etiss_dump_dir}/{target_sw}.dump"
    with open(etiss_dump_file) as etiss_dump:
        for line in etiss_dump:
            if f"<{START_LABEL}>:" in line:
                etiss_start = int(line.split(" ")[0], 16)
            if f"<{END_LABEL}>:" in line:
                etiss_end = int(line.split(" ")[0], 16)

    print_info(f"(AddressMatcher) RTL Start Address: {verilator_start:08x}")
    print_info(f"(AddressMatcher) RTL End Address: {verilator_end:08x}")
    print_info(f"(AddressMatcher) ETISS Start Address: {etiss_start:08x}")
    print_info(f"(AddressMatcher) ETISS End Address: {etiss_end:08x}")

    return {
        "e_start": etiss_start,
        "e_end": etiss_end,
        "v_start": verilator_start,
        "v_end": verilator_end,
    }


def match_length(a: list, b: list, value) -> None:
    diff = abs(len(a) - len(b))
    if len(a) > len(b):
        b.extend([value] * diff)
    elif len(a) < len(b):
        a.extend([value] * diff)


def write_out(
    outfile_path: pathlib.Path,
    matching: list[str],
    initial: list[str] | None = None,
    trailing: list[str] | None = None,
    etiss_cycles: tuple[int, int] = (0, 0),
    verilator_cycles: int = 0,
) -> None:
    with open(outfile_path, "w", encoding="utf-8") as outfile:

        longdash = 153
        shortdash = 39

        if initial:
            outfile.write("Initial:\n")
            outfile.write("-" * shortdash + "\n")
            outfile.write("ETISS              | Verilator\n")
            outfile.write("-" * shortdash + "\n")
            outfile.writelines(initial)
            outfile.write("-" * shortdash + "\n")

        outfile.write("Matching:\n")
        outfile.write("-" * longdash + "\n")
        outfile.write(
            "Instr E  | Asm E    | Instr V  | Asm V    | Delta ETISS | Delta RTL   | Diff E - V  | "
        )
        for name in PRINT_STAGES:
            outfile.write(
                name
                + " " * (MAX_STAGE_NAME_LEN + 6 if STAGE_IN_COL else 14 - len(name))
                + "| "
            )
        outfile.write("\n")
        outfile.write("-" * longdash + "\n")
        outfile.writelines(matching)
        outfile.write("-" * longdash + "\n")
        outfile.write(
            f"ETISS WB cycles:   {etiss_cycles[0]} | RTL cycles: {verilator_cycles} | Diff: {etiss_cycles[0] - verilator_cycles}\n"
        )
        outfile.write(
            f"ETISS DISP cycles: {etiss_cycles[1]} | RTL cycles: {verilator_cycles} | Diff: {etiss_cycles[1] - verilator_cycles}\n"
        )
        outfile.write("-" * longdash + "\n")

        if trailing:
            outfile.write("Trailing:\n")
            outfile.write("-" * shortdash + "\n")
            outfile.write("ETISS              | Verilator\n")
            outfile.write("-" * shortdash + "\n")
            outfile.writelines(trailing)


def read_verilator_trace(
    verilator_base_path: pathlib.Path, v_start: int, v_end: int
) -> dict:
    verilator_trace_path = verilator_base_path / f"{TARGET_SW}_trace.txt"
    verilator_transformed_trace_path = verilator_base_path / f"{TARGET_SW}_trace_t.txt"

    with open(verilator_trace_path, "r", encoding="utf-8") as verilator_trace, open(
        verilator_transformed_trace_path, "w", encoding="utf-8"
    ) as verilator_transformed_trace:

        verilator = {
            "asm": [],
            "instrs": [],
            "delta": [],
            "cycles": [],
            "start": 0,
            "end": 0,
        }

        verilator_index = 0
        for line in verilator_trace:
            split_line = line.strip().split(",")
            if len(split_line) > 3:
                pc = int(split_line[0], base=16)
                if pc == v_start:
                    print_info(
                        f"(AddressMatcher) Matched Verilator start: {verilator_index}"
                    )
                    verilator["start"] = verilator_index

                if pc == v_end:
                    print_info(
                        f"(AddressMatcher) Matched Verilator end: {verilator_index}"
                    )
                    verilator["end"] = verilator_index

                verilator["asm"].append(int(split_line[1], base=16))
                verilator["delta"].append(int(split_line[3]))
                verilator["cycles"].append(int(split_line[2]))
                instr = decoder.decode(f"{int(split_line[1], 16):032b}")
                if instr:
                    verilator["instrs"].append(instr["instr"])
                    if TRANSFORM_TRACES:
                        verilator_transformed_trace.write(f"{instr["instr"]}, {line}")
                else:
                    verilator["instrs"].append("unknown")
                    if TRANSFORM_TRACES:
                        verilator_transformed_trace.write(f"v_instr, {line}")

                verilator_index += 1

    return verilator


def read_etiss_trace(etiss_base_path: pathlib.Path, e_start: int, e_end: int) -> dict:
    etiss_trace_path = etiss_base_path / f"{TARGET_SW}_trace.txt"
    etiss_transformed_trace_path = etiss_base_path / f"{TARGET_SW}_trace_t.txt"
    etiss_timing_path = etiss_base_path / f"{TARGET_SW}_timing.csv"

    with open(etiss_trace_path, "r", encoding="utf-8") as etiss_trace, open(
        etiss_transformed_trace_path, "w", encoding="utf-8"
    ) as etiss_transformed_trace:

        etiss = {
            "asm": [0x0],
            "instrs": ["auipc"],
            "delta": [],
            "stage_cycles": {name: [] for name in TRACK_STAGES},
            "cycles": 0,
            "start": 0,
            "end": 0,
            "pc": ["0x00000000"],
        }

        # TODO: adding trace argument to perf run script skips first auipc
        etiss_index = 1
        for line in etiss_trace:
            split_line = line.split(" ")
            if len(line) > 3:
                pc = int(split_line[0][2:].lstrip("0"), base=16)
                if pc == e_start:
                    print_info(f"(AddressMatcher) Matched ETISS start: {etiss_index}")
                    etiss["start"] = etiss_index
                if pc == e_end:
                    print_info(f"(AddressMatcher) Matched ETISS end: {etiss_index}")
                    etiss["end"] = etiss_index
                etiss["asm"].append(int(split_line[4], 2))
                etiss["instrs"].append(split_line[2])
                etiss["pc"].append(split_line[0][2:])
                hex_asm = f"{int(split_line[4], 2):08x}"
                split_line[4] = hex_asm
                if TRANSFORM_TRACES:
                    etiss_transformed_trace.write(" ".join(split_line))

                etiss_index += 1
            else:
                print(line)

    with open(etiss_timing_path, "r", encoding="utf-8") as etiss_timing:
        reader = csv.reader(etiss_timing)
        previous = 0
        index = 0
        indices = {name: 0 for name in TRACK_STAGES}
        assign_stages = True
        for row in reader:
            if row[0] == "IF_stage":
                if not assign_stages:
                    continue
                for i, stage in enumerate(row):
                    print_info(f"(Timing) Available stage: {stage}")
                    if stage in TRACK_STAGES:
                        indices[stage] = i
                assign_stages = False
                continue

            row_i = indices[SCALAR_TIMING_STAGE]

            # try:
            #     instr_name = etiss["instrs"][index]
            #     if instr_name in V_SHORT_SIGNAL:
            #         row_i = indices[FAST_TIMING_STAGE]
            #     elif instr_name in VSET_INSTRS:
            #         row_i = indices[VSET_TIMING_STAGE]
            #     elif instr_name in V_LONG_SIGNAL:
            #         row_i = indices[SLOW_TIMING_STAGE]
            # except Exception as e:
            #     print("Exception: " + str(e))
            #     print(f"Error index {index}")
            #     exit(1)

            for name, stage_index in indices.items():
                etiss["stage_cycles"][name].append(int(row[stage_index]))

            cycles = int(row[row_i])
            etiss["delta"].append(cycles - previous)
            previous = cycles
            index += 1

        etiss["cycles"] = previous

    return etiss


def read_traces(etiss_base_path, verilator_base_path, addrs) -> tuple[dict, dict]:

    verilator = read_verilator_trace(
        verilator_base_path, addrs["v_start"], addrs["v_end"]
    )

    etiss = read_etiss_trace(etiss_base_path, addrs["e_start"], addrs["e_end"])

    return (etiss, verilator)


def usage() -> None:
    """Usage function"""
    print("Usage: transform.py <ARCH> <VLEN> <VLANE_WIDTH> <TARGET_SW> [-t] [-i]")
    exit(1)


def compare(
    arch,
    vlen,
    vlane_width,
    target_sw,
    write_trailing: bool = False,
    write_initial: bool = False,
) -> tuple[float, float, float, int, int, bool]:

    global ARCH, VLEN, VLANE_WIDTH, TARGET_SW

    ARCH = arch
    VLEN = vlen
    VLANE_WIDTH = vlane_width
    TARGET_SW = target_sw

    ok = True

    zvl_string = f"zvl{vlen}b"
    vlane_string = f"vlane{vlane_width}"
    full_arch_subpath = pathlib.Path(arch) / zvl_string / vlane_string
    verilator_dump_dir = (
        pathlib.Path(os.environ["WS_PATH"])
        / "vicuna2_tinyml_benchmarking"
        / "build_from_other"
        / arch
        / zvl_string
        / "dump"
    )
    etiss_dump_dir = (
        pathlib.Path(os.environ["WS_PATH"])
        / "gen_perfsim"
        / "target_sw"
        / "examples"
        / "Vicuna"
        / "custom"
        / arch
        / zvl_string
        / "dump"
    )
    check_path(verilator_dump_dir)
    check_path(etiss_dump_dir)

    print_info(blue(bold(f"Analyzing {TARGET_SW}")))

    etiss_arch_path = COMPARISON_DIR / "etiss" / full_arch_subpath
    verilator_arch_path = COMPARISON_DIR / "verilator" / full_arch_subpath
    check_path(etiss_arch_path)
    check_path(verilator_arch_path)
    etiss, verilator = read_traces(
        etiss_arch_path,
        verilator_arch_path,
        read_addresses(target_sw, verilator_dump_dir, etiss_dump_dir),
    )

    # longest_match = SequenceMatcher(
    #     None, etiss["asm"], verilator["asm"]
    # ).find_longest_match()

    # print(f"(SequenceMatcher) Matched {longest_match.size} instructions")
    n_instructions_v = verilator["end"] - verilator["start"]
    n_instructions_e = etiss["end"] - etiss["start"]
    if n_instructions_v != n_instructions_e:
        print_info("(AddressMatcher) RTL and ETISS instructions not equal!")
        ok = False

    print_info(
        f"(AddressMatcher) Verilator: ({verilator["start"]}, {verilator["end"]}): {n_instructions_v} Instructions"
    )
    print_info(
        f"(AddressMatcher) ETISS: ({etiss["start"]}, {etiss["end"]}): {n_instructions_e} Instructions"
    )

    # match_start_etiss = longest_match.a
    # match_end_etiss = longest_match.a + longest_match.size

    # match_start_verilator = longest_match.b
    # match_end_verilator = longest_match.b + longest_match.size

    # match_size = verilator["end"] - verilator["start"]

    # print(f"Verilator: Start = {verilator["start"]}, End = {verilator["end"]}")
    # print(f"ETISS: Start = {etiss["start"]}, End = {etiss["start"] + match_size}")

    match_start_etiss = etiss["start"]
    match_end_etiss = etiss["end"]

    match_start_verilator = verilator["start"]
    match_end_verilator = verilator["end"]

    delta_zip = list(
        zip(
            etiss["delta"][match_start_etiss:match_end_etiss],
            verilator["delta"][match_start_verilator:match_end_verilator],
        )
    )

    sum_diffs = sum(d_e - d_v for d_e, d_v in delta_zip)
    abs_sum_diffs = sum(abs(d_e - d_v) for d_e, d_v in delta_zip)
    max_start_cycles_e = max(
        stage[match_start_etiss] for stage in etiss["stage_cycles"].values()
    )
    cpi_e = (
        max(
            stage[match_end_etiss] - max_start_cycles_e
            for stage in etiss["stage_cycles"].values()
        )
        / n_instructions_e
    )
    cpi_v = (
        verilator["cycles"][match_end_verilator]
        - verilator["cycles"][match_start_verilator]
    ) / n_instructions_v

    cpi_factor = cpi_e / cpi_v
    error = (cpi_factor - 1) * 100

    print_info(f"(Cycles) Sum of differences: {sum_diffs}")
    print_info(f"(Cycles) Absolute sum of differences: {abs_sum_diffs}")
    print_info(
        f"(Cycles) Average difference per instruction: {abs_sum_diffs / n_instructions_e:.4f}"
    )
    print_info(f"(Cycles) CPI ETISS: {cpi_e:.4f}, CPI RTL: {cpi_v:.4f}")
    print_info(f"(Cycles) ETISS CPI is {cpi_factor * 100:.4f}% of RTL CPI")
    print_info(f"(Cycles) Error: {error :.4f}%")

    stage_cycles = list(
        zip(
            *[
                etiss["stage_cycles"][name][match_start_etiss:match_end_etiss]
                for name in PRINT_STAGES
            ]
        )
    )

    matching = [
        (
            f"{pc_e:8} |"
            f"{ins_e:8} |"
            f" {asm_e:08x} |"
            f" {ins_v:8}   |"
            f" {asm_v:08x} |"
            f" dE: {d_e:7} |"
            f" dV: {d_v:7} |"
            f" Diff: {d_e - d_v:5} |"
            f" {re.sub(r"[\[\],\']", "", str([(name + ": " if STAGE_IN_COL else "") + f"{(s_cycles[i]):13} |" for i, name in enumerate(PRINT_STAGES)]))}"
            f" WB V: {rtl_wb_cycles:10} |"
            f"{" (A!)" if asm_e != asm_v else ""}"
            f"{" (I!)" if ins_e != ins_v else ""}"
            f"{"\n(D+!)" if d_e > d_v else "\n(D-!)" if d_e < d_v else ""}"
            f"{"\n(DT!)" if abs(d_e - d_v) > DELTA_TRESHOLD else ""}"
            f"\n"
        )
        for (
            pc_e,
            asm_e,
            ins_e,
            asm_v,
            ins_v,
            d_e,
            d_v,
            s_cycles,
            rtl_wb_cycles,
        ) in zip(
            etiss["pc"][match_start_etiss:match_end_etiss],
            etiss["asm"][match_start_etiss:match_end_etiss],
            etiss["instrs"][match_start_etiss:match_end_etiss],
            verilator["asm"][match_start_verilator:match_end_verilator],
            verilator["instrs"][match_start_verilator:match_end_verilator],
            etiss["delta"][match_start_etiss:match_end_etiss],
            verilator["delta"][match_start_verilator:match_end_verilator],
            stage_cycles,
            verilator["cycles"][match_start_verilator:match_end_verilator],
        )
    ]

    initial = None
    trailing = None

    if write_initial:
        etiss_initial = etiss["asm"][:match_start_etiss]
        etiss_instrs_initial = etiss["instrs"][:match_start_etiss]
        verilator_initial = verilator["asm"][:match_start_verilator]
        verilator_instrs_initial = verilator["instrs"][:match_start_verilator]
        match_length(etiss_initial, verilator_initial, -1)
        match_length(etiss_instrs_initial, verilator_instrs_initial, "-")

        initial = [
            f"{e_i:8}: {e:08x} | {v_i:8}: {v:08x}\n"
            for (e_i, e, v_i, v) in zip(
                etiss_instrs_initial,
                etiss_initial,
                verilator_instrs_initial,
                verilator_initial,
            )
        ]

    if write_trailing:
        etiss_trailing = etiss["asm"][match_end_etiss:]
        etiss_instrs_trailing = etiss["instrs"][match_end_etiss:]
        verilator_trailing = verilator["asm"][match_end_verilator:]
        verilator_instrs_trailing = verilator["instrs"][match_end_verilator:]
        match_length(etiss_trailing, verilator_trailing, -1)
        match_length(etiss_instrs_trailing, verilator_instrs_trailing, "-")

        trailing = [
            f"{e_i:8}: {e:08x} | {v_i:8}: {v:08x}\n"
            for (e_i, e, v_i, v) in zip(
                etiss_instrs_trailing,
                etiss_trailing,
                verilator_instrs_trailing,
                verilator_trailing,
            )
        ]

    # TODO
    etiss_cycles = (
        etiss["stage_cycles"]["WB_stage"][match_end_etiss - 1]
        - etiss["stage_cycles"]["WB_stage"][match_start_etiss],
        etiss["stage_cycles"]["V_DISP_stage"][match_end_etiss - 1]
        - etiss["stage_cycles"]["V_DISP_stage"][match_start_etiss],
    )

    outfile_path: pathlib.Path = (
        COMPARISON_DIR
        / "match"
        / ARCH
        / f"zvl{VLEN}b"
        / f"vlane{VLANE_WIDTH}"
        / f"match_{TARGET_SW}.txt"
    )
    outfile_path.parent.mkdir(parents=True, exist_ok=True)
    write_out(
        outfile_path,
        matching,
        initial,
        trailing,
        etiss_cycles,
        verilator["cycles"][match_end_verilator - 1]
        - verilator["cycles"][match_start_verilator],
    )

    return (cpi_e, cpi_v, error, abs_sum_diffs, n_instructions_e, ok)


if __name__ == "__main__":

    # TODO: argparse
    arch = sys.argv[1]
    vlen = int(sys.argv[2])
    vlane_width = int(sys.argv[3])
    target_sw = sys.argv[4]

    write_trailing = False
    write_initial = False

    if "-t" in sys.argv:
        write_trailing = True
    if "-i" in sys.argv:
        write_initial = True

    compare(arch, vlen, vlane_width, target_sw, write_trailing, write_initial)
