import pathlib
import csv

from comp_util import print_info, match_length
import decoder

START_LABEL = "address_match_start"
END_LABEL = "address_match_end"


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


def parse_etiss_line(line: str):
    fields = ()
    split_line = line.split(" ")
    pc = int(split_line[0][2:].lstrip("0"), base=16)
    
    pass

def seek_start(address: int, file) -> tuple[str, int]:
    '''Returns the line and index of the match start''' 
    for line in file:
        pass
        # if 


def analyze_traces(
    target_sw: str,
    etiss_base_path: pathlib.Path,
    verilator_base_path: pathlib.Path,
    addresses: dict[str, int],
    write_match: bool,
) -> bool:

    verilator_trace_path = verilator_base_path / f"{target_sw}_trace.txt"
    etiss_trace_path = etiss_base_path / f"{target_sw}_trace.txt"
    etiss_timing_path = etiss_base_path / f"{target_sw}_timing.csv"

    with open(etiss_trace_path, "r", encoding="utf-8") as etiss_trace, open(
        verilator_trace_path, "r", encoding="utf-8"
    ) as verilator_trace, open(
        etiss_timing_path, "r", encoding="utf-8"
    ) as etiss_timing:

        # ETISS trace skips first instruction
        etiss_index = 1
        etiss_timing_index = 0
        verilator_index = 0
