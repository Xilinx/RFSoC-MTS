# -------------------------------------------------------------------------------------------------
# Copyright (C) 2023 Advanced Micro Devices, Inc
# SPDX-License-Identifier: MIT
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --

set overlay_name [lindex $argv 0]
set design_name [lindex $argv 0]

# Open project
open_project ./${overlay_name}/${overlay_name}.xpr
open_bd_design ./${overlay_name}/${overlay_name}.srcs/sources_1/bd/${design_name}/${design_name}.bd

# Add top wrapper and xdc files
make_wrapper -files [get_files ./${overlay_name}/${overlay_name}.srcs/sources_1/bd/${design_name}/${design_name}.bd] -top
add_files -norecurse ./${overlay_name}/${overlay_name}.gen/sources_1/bd/${design_name}/hdl/${design_name}_wrapper.vhd
set_property top ${design_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

# Call implement
launch_runs impl_1 -to_step write_bitstream -jobs 12
wait_on_run impl_1

