# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The pinned reference subject's system prompt (issue #43; ADR-0007).

The reference subject is Inspect's ReAct agent with ``bash()`` only
(controlled-interface mode). Its prompt is part of the system identity: the
SystemSpec records this text's digest, so any edit is a new system. The prompt
gives no grading hints: no labels, no scoring rules, no feedback.
"""

from __future__ import annotations

import hashlib

REFERENCE_PROMPT = """\
You are a careful security reviewer working in a sandbox with no network access.
The workspace contains a small codebase. Use the bash tool to read the code.
Report only defects you believe are real, as the task instructions describe,
by writing findings.json in the workspace root. When you are done, call submit.
"""


def reference_prompt_digest() -> str:
    return hashlib.sha256(REFERENCE_PROMPT.encode("utf-8")).hexdigest()
