# Instructions that signal completion after the V-Execute stage

RED_VV = [
    "vredsum_vs",
    "vredmaxu_vs",
    "vredmax_vs",
    "vredminu_vs",
    "vredmin_vs",
    "vredand_vs",
    "vredor_vs",
    "vredxor_vs",
]

ELEM_VV = [
    "vcompress_vm",
]

LSU = [
    "vle32_v",
    "vle16_v",
    "vle8_v",
    "vse32_u",
    "vse16_u",
    "vse8_u",
    "vsr_v",
    "vl8r_v",
    "vl16r_v",
    "vl32r_v",
]


VWXUNARY0 = ["vmv_x_s", "vcpop_m", "vfirst_m"]

V_LONG_SIGNAL = LSU + VWXUNARY0

INT_ARITH_VMV = ["vmv_v_v", "vmv_v_x", "vmv_v_i"]
INT_ARITH_VMERGE = ["vmerge_vvm", "vmerge_vxm", "vmerge_vim"]
INT_EXT = ["vsext_vf2", "vsext_vf4", "vsext_vf8", "vzext_vf2", "vzext_vf4", "vzext_vf8"]
INT_ARITH_VV = [
    "vadd_vv",
    "vsub_vv",
    "vwaddu_vv",
    "vwsubu_vv",
    "vwadd_vv",
    "vwsub_vv",
    "vwaddu_w_vv",
    "vwsubu_w_vv",
    "vwadd_w_vv",
    "vwsub_w_vv",
    "vadc_vvm",
    "vmadc_vv",
    "vsbc_vvm",
    "vmsbc_vv",
    "vand_vv",
    "vor_vv",
    "vxor_vv",
    "vsll_vv",
    "vsrl_vv",
    "vsra_vv",
    "vmseq_vv",
    "vmsne_vv",
    "vmsltu_vv",
    "vmslt_vv",
    "vmsleu_vv",
    "vmsle_vv",
    "vminu_vv",
    "vmin_vv",
    "vmaxu_vv",
    "vmax_vv",
    "vmul_vv",
    "vmulh_vv",
    "vmulhu_vv",
    "vmulhsu_vv",
    "vdivu_vv",
    "vdiv_vv",
    "vremu_vv",
    "vrem_vv",
    "vwmul_vv",
    "vwmulu_vv",
    "vwmulsu_vv",
    "vmacc_vv",
    "vnmsac_vv",
    "vmadd_vv",
    "vnmsub_vv",
    "vwmaccu_vv",
    "vwmacc_vv",
    "vwmaccsu_vv",
    "vmerge_vvm",
    "vsaddu_vv",
    "vsadd_vv",
    "vssubu_vv",
    "vssub_vv",
    "vaaddu_vv",
    "vaadd_vv",
    "vasubu_vv",
    "vasub_vv",
    "vsmul_vv",
    "vssrl_vv",
    "vssra_vv",
]

INT_ARITH_VX = [
    "vadd_vx",
    "vsub_vx",
    "vrsub_vx",
    "vwaddu_vx",
    "vwsubu_vx",
    "vwadd_vx",
    "vwsub_vx",
    "vwaddu_w_vx",
    "vwsubu_w_vx",
    "vwadd_w_vx",
    "vwsub_w_vx",
    "vadc_vxm",
    "vmadc_vxm",
    "vmadc_vx",
    "vsbc_vxm",
    "vmsbc_vxm",
    "vmsbc_vx",
    "vand_vx",
    "vor_vx",
    "vxor_vx",
    "vsll_vx",
    "vsrl_vx",
    "vsra_vx",
    "vmseq_vx",
    "vmsne_vx",
    "vmsltu_vx",
    "vmslt_vx",
    "vmsleu_vx",
    "vmsle_vx",
    "vmsgtu_vx",
    "vmsgt_vx",
    "vminu_vx",
    "vmin_vx",
    "vmaxu_vx",
    "vmax_vx",
    "vmul_vx",
    "vmulh_vx",
    "vmulhu_vx",
    "vmulhsu_vx",
    "vdivu_vx",
    "vdiv_vx",
    "vremu_vx",
    "vrem_vx",
    "vwmul_vx",
    "vwmulu_vx",
    "vwmulsu_vx",
    "vmacc_vx",
    "vnmsac_vx",
    "vmadd_vx",
    "vnmsub_vx",
    "vwmaccu_vx",
    "vwmacc_vx",
    "vwmaccsu_vx",
    "vwmaccus_vx",
    "vmerge_vxm",
    "vsaddu_vx",
    "vsadd_vx",
    "vssubu_vx",
    "vssub_vx",
    "vaaddu_vx",
    "vaadd_vx",
    "vasubu_vx",
    "vasub_vx",
    "vsmul_vx",
    "vssrl_vx",
    "vssra_vx",
    "vslideup_vx",
    "vslidedown_vx",
    "vslide1up_vx",
    "vslide1down_vx",
]

INT_ARITH_VI = [
    "vadd_vi",
    "vrsub_vi",
    "vadc_vim",
    "vmadc_vim",
    "vmadc_vi",
    "vand_vi",
    "vor_vi",
    "vxor_vi",
    "vsll_vi",
    "vsrl_vi",
    "vsra_vi",
    "vmseq_vi",
    "vmsne_vi",
    "vmsleu_vi",
    "vmsle_vi",
    "vmsgtu_vi",
    "vmsgt_vi",
    "vmerge_vim",
    "vsaddu_vi",
    "vsadd_vi",
    "vssrl_vi",
    "vssra_vi",
    "vslideup_vi",
    "vslidedown_vi",
]

V_SHORT_SIGNAL = (
    INT_ARITH_VV
    + INT_ARITH_VX
    + INT_ARITH_VI
    + INT_ARITH_VMV
    + INT_ARITH_VMERGE
    + INT_EXT
    + RED_VV
    + ["vmv_s_x"]
)

# V_RESULT_SIGNAL = V_MOVE_TO_SCALAR

# INT_REDUCE = [
#     "vrgather_vv",
#     "vrgatherei16_v",
# ]
