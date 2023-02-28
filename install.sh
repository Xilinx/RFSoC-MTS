# -------------------------------------------------------------------------------------------------
# Copyright (C) 2023 Advanced Micro Devices, Inc
# SPDX-License-Identifier: MIT
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --

#!/bin/bash

# Build MTS necessary patch to xrfdc package
echo "Cloning the PYNQ repository"
git clone https://github.com/xilinx/PYNQ
cd PYNQ
git apply ../boards/patches/xrfdc_mts.patch

pushd sdbuild/packages/xrfdc
. pre.sh
. qemu.sh
popd
cd ..

# Create a device-tree overlay to access PL-DRAM
sudo apt-get update -y
sudo apt-get install -y device-tree-compiler
cd boards/ZCU208/dts
make
cp ddr4.dtbo ../../../rfsoc_mts/
cd ../../..

# Install python package and notebook
python3 -m pip install . --no-build-isolation
pynq-get-notebooks RFSoC-MTS -p $PYNQ_JUPYTER_NOTEBOOKS
