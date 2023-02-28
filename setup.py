# -------------------------------------------------------------------------------------------------
# Copyright (C) 2023 Advanced Micro Devices, Inc
# SPDX-License-Identifier: MIT
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --
from pynqutils.setup_utils import build_py, find_version, extend_package
from setuptools.command.build_ext import build_ext
from setuptools import setup, find_packages, Distribution
from distutils.dir_util import copy_tree
import os
import shutil 

module_name = "rfsoc_mts"
board_name = os.environ['BOARD']

data_files = []

def copy_xrfclk():
    src_at_dir = os.path.join('boards', board_name, 'xrfclk')
    dst_at_dir = os.path.join('xrfclk')
    copy_tree(src_at_dir, dst_at_dir)
    data_files.extend(
        [os.path.join("..", dst_at_dir, f) for f in os.listdir(dst_at_dir)])

def copy_notebooks():
    src_at_dir = os.path.join('boards', board_name, 'notebooks')
    dst_at_dir = os.path.join(module_name, 'notebooks')
    copy_tree(src_at_dir, dst_at_dir)
    data_files.extend(
        [os.path.join("..", dst_at_dir, f) for f in os.listdir(dst_at_dir)])

with open("README.md", encoding='utf-8') as fh:
    readme_lines = fh.readlines()[2:47]
long_description = (''.join(readme_lines))

def resolve_overlay_d(path):
    """ Resolve overlay files by moving the cached copy """
    subfolders = [os.path.abspath(f.path) for f in os.scandir(path)
                  if f.is_dir() and f.path.endswith('.d')]
    for f in subfolders:
        dst_name = f.rstrip('.d')
        file_list = [os.path.join(f, x) for x in os.listdir(f)]
        if not file_list:
            raise FileNotFoundError("Folder {} is empty.".format(f))
        shutil.copy(file_list[0], dst_name)
        shutil.rmtree(f)

class BuildExtension(build_ext):
    """A custom build extension for adding user-specific options.
    """
    def run(self):
        build_ext.run(self)
        overlay_path = os.path.join(self.build_lib, module_name)
        resolve_overlay_d(overlay_path)

# Enforce platform-dependent distribution
class CustomDistribution(Distribution):
    def has_ext_modules(self):
        return True

copy_xrfclk()
copy_notebooks()
extend_package(module_name, data_files)

setup(
    name=module_name,
    version=find_version('{}/__init__.py'.format(module_name)),
    description="RFSoC-PYNQ example design showcasing MTS and PL-DDR4 deep capture",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    package_data={
        "": data_files,
    },
    python_requires=">=3.10.0",
    install_requires=[
        "xrfdc==2.0",
        "pynqutils",
        "matplotlib",
        "ipython"
    ],
    entry_points={
        "pynq.notebooks": [
            "RFSoC-MTS = {}.notebooks".format(
                module_name)
        ]
    },
    cmdclass={"build_py": build_py,
              "build_ext": BuildExtension},
    distclass=CustomDistribution
)
