#!/usr/bin/env python3

import os
import pathlib
import subprocess
import multiprocessing as mp

# TODO: remove WS_PATH stuff
WS_PATH_ENV_NAME = "WS_PATH"
WS_PATH_ENV = os.getenv(WS_PATH_ENV_NAME)
if not WS_PATH_ENV:
    print(f'Environment Variable "{WS_PATH_ENV_NAME}" not set')
    exit()

WS_PATH = pathlib.Path(WS_PATH_ENV)
PERFSIM_PRJ_SRC = WS_PATH / "gen_perfsim"
VERILATOR_PRJ_SRC = WS_PATH / "vicuna2_tinyml_benchmarking"
QEMU_PRJ_SRC = WS_PATH / "qemu-testing"

INSTR_COUNT = {
    "tflm_vww": {
        128: 71298379,
        256: 68974858,
        512: 69103622,
        1024: 74900400,
    },
    "tflm_toy": {
        128: 587766,
        256: 414096,
        512: 325618,
        1024: 282058,
    },
    "tflm_aww": {
        128: 29016385,
        256: 27607588,
        512: 26906876,
        1024: 26554756,
    },
}

N_RUNS = 10


def run_etiss(arch, vlen, target, enable_perf: bool) -> float:
    etiss_script = PERFSIM_PRJ_SRC / "run-target-simple.sh"
    etiss_args = [
        etiss_script,
        "--arch",
        arch,
        "--vlen",
        str(vlen),
        "--target",
        target,
    ]

    if enable_perf:
        etiss_args.append("--perf")

    etiss_proc = subprocess.run(args=etiss_args, capture_output=True, encoding="utf-8")
    etiss_lines = etiss_proc.stderr.split("\n")
    # print(etiss_proc.stdout)
    for line in etiss_lines:
        if "user" in line:
            e_usertime = line[4:].strip()[2:-1]
            return float(e_usertime)

    return -1


def run_verilator(arch, vlen, vlane_width, target) -> float:
    verilator_script = VERILATOR_PRJ_SRC / "run-target.sh"
    verilator_args = [
        verilator_script,
        "--arch",
        arch,
        "--vlen",
        str(vlen),
        "--vlane_width",
        str(vlane_width),
        "--target",
        target,
    ]

    verilator_proc = subprocess.run(
        args=verilator_args, capture_output=True, encoding="utf-8"
    )
    verilator_lines = verilator_proc.stderr.split("\n")
    for line in verilator_lines:
        if "user" in line:
            v_usertime_split = line[4:].strip().split("m")
            v_usertime_s = float(v_usertime_split[1][:-1])
            v_usertime_m = int(v_usertime_split[0])
            return (v_usertime_m * 60) + v_usertime_s

    return -1


def run_qemu(arch, vlen, target) -> float:
    qemu_script = QEMU_PRJ_SRC / "run-target.sh"
    qemu_args = [
        qemu_script,
        "--arch",
        arch,
        "--vlen",
        str(vlen),
        "--target",
        target,
    ]

    qemu_proc = subprocess.run(args=qemu_args, capture_output=True, encoding="utf-8")
    # print(qemu_proc.stderr)
    qemu_lines = qemu_proc.stderr.split("\n")
    for line in qemu_lines:
        if "user" in line:
            q_usertime = line[4:].strip()[2:-1]
            return float(q_usertime)

    return -1


def main():
    arch = "rv32im_zve32x"
    vlens = [128, 256, 512, 1024]
    vlane_widths = [32, 64, 128]
    targets = ["tflm_toy", "tflm_aww", "tflm_vww"]
    # targets = ["tflm_aww"]

    for target in targets:
        for vlen in vlens:
            res_q = []
            res_e = []
            res_e_perf = []
            for i in range(N_RUNS):
                res_q.append(run_qemu(arch, vlen, target))
                res_e.append(run_etiss(arch, vlen, target, False))
                res_e_perf.append(run_etiss(arch, vlen, target, True))

            instr_cnt = INSTR_COUNT[target][vlen]

            avg_time_q = sum(res_q) / N_RUNS
            avg_mips_q = (instr_cnt / avg_time_q) / 1000000
            print(
                f"{target} & QEMU & {vlen} & - & {avg_time_q:.4f}s & {avg_mips_q:.4f} & {instr_cnt}"
            )

            avg_time_e = sum(res_e) / N_RUNS
            avg_mips_e = (instr_cnt / avg_time_e) / 1000000
            print(
                f"{target} & ETISS & {vlen} & - & {avg_time_e:.4f}s & {avg_mips_e:.4f} & {instr_cnt}"
            )

            avg_time_e_perf = sum(res_e_perf) / N_RUNS
            avg_mips_e_perf = (instr_cnt / avg_time_e_perf) / 1000000
            print(
                f"{target} & ETISS + Perf. Est. & {vlen} & - & {avg_time_e_perf:.4f}s & {avg_mips_e_perf:.4f} & {instr_cnt}"
            )

            for vlane_width in vlane_widths:
                if vlane_width > vlen / 2:
                    continue

                time_v = run_verilator(arch, vlen, vlane_width, target)
                mips_v = (instr_cnt / time_v) / 1000000
                print(f"{target} & Verilator & {vlen} & {vlane_width} & {time_v:.4f} s & {mips_v:.4f} & {instr_cnt} \\")

            # with mp.Pool(processes=32) as pool:
            # args_e = [(arch, vlen, target) for i in range(N_RUNS)]
            # args_q = [(arch, vlen, target) for i in range(N_RUNS)]
            # res_e = pool.starmap(run_etiss, args_e)
            # res_q = pool.starmap(run_qemu, args_q)
            # avg_time_e = sum(res_e) / N_RUNS
            # avg_time_q = sum(res_q) / N_RUNS
            # avg_mips_e = (INSTR_COUNT[target][vlen] / avg_time_e) / 1000000
            # avg_mips_q = (INSTR_COUNT[target][vlen] / avg_time_q) / 1000000
            # print(f"{target} & ETISS NP & {vlen} & - & {avg_time_e:.4f} s & {avg_mips_e:.4f}")
            # print(f"{target} & QEMU & {vlen} & - & {avg_time_q:.4f} s & {avg_mips_q:.4f}")
            # for vlane_width in vlane_widths:
            #     if vlane_width > vlen / 2:
            #         continue
            #     args_v = [(arch, vlen, vlane_width, target) for i in range(N_RUNS)]
            #     res_v = pool.starmap(run_verilator, args_v)
            #     avg_time_v = sum(res_v) / N_RUNS
            #     instr_count = INSTR_COUNT[target][vlen]
            #     avg_mips_v = (instr_count / avg_time_v) / 1000000
            #     print(f"{target} & Verilator & {vlen} & {vlane_width} & {avg_time_v:.4f} s & {avg_mips_v:.4f} & {instr_count} \\")


if __name__ == "__main__":
    main()
