# -------------------------------------------------------------------------------------------------
# Copyright (C) 2023 Advanced Micro Devices, Inc
# SPDX-License-Identifier: MIT
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --

all: block_design bitstream check_timing handoff
	@echo
	@tput setaf 2 ; echo "Built overlays successfully!!"; tput sgr0;
	@echo

block_design:
	vivado -mode batch -source mts.tcl

bitstream:
	vivado -mode batch -source build_bitstream.tcl -notrace -tclargs mts

check_timing:
	vivado -mode batch -source check_timing.tcl -notrace -tclargs mts

handoff:
	vivado -mode batch -source handoff.tcl -notrace -tclargs mts

clean:
	rm -rf mts *.jou *.log NA .Xil *.xsa *.hwh *.bit
