# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
# ClusterFuzzLite build image for the untrusted-input parsers. Pinned by digest.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:21f6fab17ace4dc76e1c56de91ee95d3d03da021df94b41056ba036f6c6f55e9
COPY . $SRC/aureproof
WORKDIR $SRC/aureproof
COPY .clusterfuzzlite/build.sh $SRC/
