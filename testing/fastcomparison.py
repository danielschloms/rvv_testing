import pathlib
import os

from comp_util import print_info, match_length
from util import check_path, error

START_LABEL = "address_match_start"
END_LABEL = "address_match_end"


def read_addresses(
    target_sw: str, verilator_dump_dir: pathlib.Path, etiss_dump_dir: pathlib.Path
) -> tuple[dict, bool]:
    """Returns a dictionary with start and end addresses."""
    fname = "CMP: read_addresses"
    verilator_start = 0
    verilator_end = 0
    etiss_start = 0
    etiss_end = 0

    ok = True

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
        ok = False

    if verilator_start == 0:
        error(fname, "Error Verilator start")
    if verilator_end == 0:
        error(fname, "Error Verilator end")

    etiss_dump_file = f"{etiss_dump_dir}/{target_sw}.dump"
    try:
        with open(etiss_dump_file) as etiss_dump:
            for line in etiss_dump:
                if f"<{START_LABEL}>:" in line:
                    etiss_start = int(line.split(" ")[0], 16)
                if f"<{END_LABEL}>:" in line:
                    etiss_end = int(line.split(" ")[0], 16)
    except:
        print_info(f"(AddressMatcher) Could not find {target_sw} Verilator dump")
        ok = False

    if etiss_start == 0:
        error(fname, "Error ETISS start")
    if etiss_end == 0:
        error(fname, "Error ETISS end")

    # print(f"(AddressMatcher) RTL Start Address: {verilator_start:08x}")
    # print(f"(AddressMatcher) RTL End Address: {verilator_end:08x}")
    # print(f"(AddressMatcher) ETISS Start Address: {etiss_start:08x}")
    # print(f"(AddressMatcher) ETISS End Address: {etiss_end:08x}")

    return {
        "e_start": etiss_start,
        "e_end": etiss_end,
        "v_start": verilator_start,
        "v_end": verilator_end,
    }, ok


def parse_etiss_line(line: str):
    split_line = line.split(" ")
    pc = int(split_line[0][2:].lstrip("0"), base=16)
    asm = int(split_line[4], 2)
    instr = split_line[2]
    return pc, asm, instr


def parse_verilator_line(line: str):
    split_line = line.strip().split(",")
    try:
        pc = int(split_line[0], base=16)
        asm = int(split_line[1], base=16)
        delta = int(split_line[3])
        cycles = int(split_line[2])
        return pc, asm, cycles, delta
    except:
        print(line)
        exit()


def parse_stages(line: str) -> dict[str, int]:
    split_line = line.strip().split(",")
    stages = {}
    for i, stage in enumerate(split_line):
        stages[stage] = i
    return stages


def analyze_traces(
    target_sw: str,
    etiss_base_path: pathlib.Path,
    verilator_base_path: pathlib.Path,
    match_path: pathlib.Path,
    addresses: dict[str, int],
    write_match: bool,
    keep_traces: bool = False,
    print_stages: bool = True,
) -> bool:

    verilator_trace_path = verilator_base_path / f"{target_sw}_trace.txt"
    etiss_trace_path = etiss_base_path / f"{target_sw}_trace.txt"
    etiss_timing_path = etiss_base_path / f"{target_sw}_timing.csv"

    with open(etiss_trace_path, "r", encoding="utf-8") as etiss_trace, open(
        verilator_trace_path, "r", encoding="utf-8"
    ) as verilator_trace, open(
        etiss_timing_path, "r", encoding="utf-8"
    ) as etiss_timing, open(
        match_path, "w", encoding="utf-8"
    ) as match_file:

        stage_line = etiss_timing.readline()
        stages = parse_stages(stage_line)
        stages_to_print = stages.keys() if print_stages else []

        # Skip first line (ETISS trace skips first instruction)
        etiss_timing.readline()
        verilator_trace.readline()

        timing_stage_index = stages["EX_stg"]

        # stages_to_print = [
        #     "IF_stage",
        #     "ID_stage",
        #     "EX_stage",
        #     "WB_stage",
        #     "V_ID_stage",
        #     "V_IQ_stage",
        #     "V_DISP_stage",
        #     "V_EX_LSU_ELM_Pack_substage",
        #     "V_RES_stage",
        # ]

        sum_diff = 0
        cycles_e_prev = 0
        cycles_e_start = 0
        cycles_v_start = 0

        # Skip to start address ETISS
        start_found_e = False
        start_found_v = False
        while True:
            timing_line = etiss_timing.readline()
            if timing_line[0] == "I":
                continue

            etiss_line = etiss_trace.readline()
            pc_e, _, _ = parse_etiss_line(etiss_line)
            if pc_e == addresses["e_start"]:
                cycles_e_prev = int(timing_line.strip().split(",")[timing_stage_index])
                cycles_e_start = cycles_e_prev
                start_found_e = True
                break

        # Skip to start address Verilator
        while True:
            verilator_line = verilator_trace.readline()
            pc_v, asm, cycles, delta = parse_verilator_line(verilator_line)
            if pc_v == addresses["v_start"]:
                cycles_v_start = cycles
                start_found_v = True
                break

        if not (start_found_e and start_found_v):
            print("Error!")
            return (0, 0, 0, 0, 0, False)

        n_instrs = 0
        running_cycles_v = 0
        nonzero_diffs = 0
        # Analyze
        while True:
            timing_line = etiss_timing.readline()
            if not timing_line:
                break
            if timing_line[0] == "I":
                continue

            etiss_trace_line = etiss_trace.readline()
            verilator_trace_line = verilator_trace.readline()

            pc_e, asm_e, instr = parse_etiss_line(etiss_trace_line)
            pc_v, asm_v, cycles_v, delta_v = parse_verilator_line(verilator_trace_line)

            if pc_e == addresses["e_end"] or pc_v == addresses["v_end"]:
                break

            running_cycles_v = cycles_v
            n_instrs += 1

            timing_split = timing_line.strip().split(",")
            cycles_e = int(timing_split[timing_stage_index])
            delta_e = cycles_e - cycles_e_prev

            delta_diff = delta_e - delta_v
            if delta_diff != 0:
                nonzero_diffs = nonzero_diffs + 1
            sum_diff = sum_diff + abs(delta_diff)

            cycles_e_prev = cycles_e

            if write_match:
                match_file.write(
                    f"{pc_e:08x} | {instr:10} | {asm_e:08x} | {asm_v:08x} | dE: {delta_e:4} | dV: {delta_v:4} | diff: {delta_diff:4} | "
                )
                stage_str = "".join(
                    [
                        f"{stage}: {timing_split[stages[stage]]} | "
                        for stage in stages_to_print
                    ]
                )
                match_file.write(stage_str + "\n")

        total_cycles_e = cycles_e_prev - cycles_e_start
        total_cycles_v = running_cycles_v - cycles_v_start
        cpi_e = total_cycles_e / n_instrs
        cpi_v = total_cycles_v / n_instrs
        cpi_error_pct = ((cpi_e / cpi_v) - 1) * 100

    if not keep_traces:
        # Delete traces
        verilator_trace_path.unlink()
        etiss_trace_path.unlink()
        etiss_timing_path.unlink()

    return (cpi_e, cpi_v, cpi_error_pct, sum_diff, n_instrs, True)


def compare_fast(
    arch,
    vlen,
    vlane_width,
    target_sw,
    keep_traces,
    print_stages,
    write_match
) -> tuple[float, float, float, int, int, bool]:
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

    comparison_dir = pathlib.Path(__file__).parent.parent / "comparison"
    etiss_arch_path = comparison_dir / "etiss" / full_arch_subpath
    verilator_arch_path = comparison_dir / "verilator" / full_arch_subpath
    check_path(verilator_dump_dir)
    check_path(etiss_dump_dir)
    check_path(etiss_arch_path)
    check_path(verilator_arch_path)

    addresses, ok_addresses = read_addresses(
        target_sw, verilator_dump_dir, etiss_dump_dir
    )
    if not ok_addresses:
        return (0, 0, 0, 0, 0, False)

    match_path: pathlib.Path = (
        comparison_dir
        / "match"
        / arch
        / f"zvl{vlen}b"
        / f"vlane{vlane_width}"
        / f"match_{target_sw}.txt"
    )
    match_path.parent.mkdir(parents=True, exist_ok=True)

    return analyze_traces(
        target_sw,
        etiss_arch_path,
        verilator_arch_path,
        match_path,
        addresses,
        write_match=write_match,
        keep_traces=keep_traces,
        print_stages=print_stages,
    )
