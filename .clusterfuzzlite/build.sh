#!/bin/bash -eu
# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
# The builder image ships Python 3.11. The fuzzed modules are 3.11-compatible
# (this build fails if they stop being); the package requires 3.12 otherwise.
pip3 install --require-hashes -r .clusterfuzzlite/requirements.txt
# Build the wheel offline with the hashed backend, then install it alone:
# its dependencies came from the hashed file above.
python3 -m hatchling build -t wheel -d /tmp/aureproof-dist
pip3 install --no-deps --ignore-requires-python /tmp/aureproof-dist/*.whl
for fuzzer in "$SRC"/aureproof/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$fuzzer"
done
