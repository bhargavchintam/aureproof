#!/bin/bash -eu
# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
# The builder image ships Python 3.11. The fuzzed modules are 3.11-compatible
# (this build fails if they stop being); the package requires 3.12 otherwise.
pip3 install --ignore-requires-python .
for fuzzer in "$SRC"/aureproof/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$fuzzer"
done
