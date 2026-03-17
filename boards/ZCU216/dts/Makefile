# -------------------------------------------------------------------------------------------------
# Copyright (C) 2023 Advanced Micro Devices, Inc
# SPDX-License-Identifier: MIT
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --
NAME = ddr4

all:
	dtc -I dts -O dtb -o $(NAME).dtbo $(NAME).dts -q

clean:
	rm -rf $(NAME).dtbo
