<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Provider terms review

- Reviewed **2026-10-27** against primary sources (issue #18, AP-041). Re-check before
  the first public results, and whenever a provider is added or a policy's effective
  date passes.
- This is an engineering summary to keep the project inside the terms. It is **not legal
  advice**. Quotes are verbatim and short.
- Provider in use for v0.1: **Anthropic**, through the API (ADR-0007). OpenAI is not used
  yet; its terms are recorded for when it is.

## Anthropic (in use)

| Source | Version checked | Relevant text |
| --- | --- | --- |
| [Usage Policy](https://www.anthropic.com/legal/aup) ([version in force](https://www.anthropic.com/legal/archive/22742366-2ef0-4c7a-a833-6523f10d3944)) | In force: Sep 15, 2025. Published, effective **Nov 12, 2026** | Prohibits: "Discover or exploit vulnerabilities in systems, networks, or applications without authorization of the system owner." The Nov 12, 2026 version adds: "This section does not prohibit security research, testing, or tool development conducted on systems you own or operate…" |
| Usage Policy: safeguards | Both versions | Prohibits intentionally bypassing "capabilities, restrictions, or guardrails". The Nov 2026 version says "bypass or interfere with", and adds a ban on multiple accounts used to "circumvent product guardrails". It also says "encountering a block does not by itself indicate a violation of the Usage Policy." |
| Usage Policy: training | Both versions | Prohibits using outputs "to train an AI model (e.g., 'model scraping' or 'model distillation') without prior authorization from Anthropic". |
| Usage Policy: access route | Nov 12, 2026 | Prohibits providing access "through unauthorized means, including services that route requests through consumer subscriptions…". |
| [Commercial Terms](https://www.anthropic.com/legal/commercial-terms) | Effective Jun 17, 2025 | D.4: no access "to build a competing product or service, including to train competing AI models". D.3: "It is Customer's responsibility to evaluate whether Outputs are appropriate… before using or sharing Outputs." The customer "owns its Outputs". No clause restricts publishing benchmarks. |
| [Cyber Verification Program](https://support.claude.com/en/articles/14604842-cyber-verification-program) | Updated Oct 2026 | Offers "reduced blocking classifiers" (tiers: Defense, Red Team, Specialized; individuals: Defense only). Says nothing about publication. |

Not found (unverified): an Anthropic trademark or brand-guideline page; any Anthropic
program terms for publishing safety evaluations.

## OpenAI (not used in v0.1)

| Source | Version checked | Relevant text |
| --- | --- | --- |
| [Sharing & Publication Policy](https://openai.com/policies/sharing-publication-policy/) | Updated 14 Nov 2022, still listed among the OpenAI Policies | "Manually review each generation before sharing"; "Indicate that the content is AI-generated in a way no user could reasonably miss or misunderstand"; "we welcome research publications related to the OpenAI API." Security issues go through its Coordinated Vulnerability Disclosure Program. |
| [Services Agreement](https://openai.com/policies/services-agreement/) | Effective Jan 1, 2026 | 3.3(e): no using Output "to develop artificial intelligence models that compete with OpenAI's products". 3.3(h): no circumventing "rate limits or restrictions or bypass any protective measures or safety mitigations". §10: no use of the other party's name or logo. Output is Customer Content, which is **Confidential Information**. |
| [Usage Policies](https://openai.com/policies/usage-policies/) | Version effective Nov 20, 2026 (the earlier version was not checked) | Permits "research, software development, model evaluation and benchmarking". Prohibits "unsolicited safety testing" and "circumventing our safeguards". Outputs "from product use or evaluation" may not be used for training. |
| [Brand guidelines](https://openai.com/brand/) | No date shown | Don't "imply endorsement"; reference model names in a way that's "precise and accurate". |

## Rules this project follows

Each rule comes only from the verified text above. Where a rule is enforced in code, the
enforcement is named.

1. **Authorized targets only.** Agents evaluate self-authored synthetic fixtures in a
   no-network sandbox (`RESPONSIBLE_USE.md`; threat model T-ELEV-1).
2. **Never bypass safeguards; never retry refusals.** A refusal is recorded as
   `safety_refusal`, never retried or reframed. Enforced: `SystemSpec` rejects
   `retry_refusals ≠ 0`, and Claude Code systems must set it to 0 explicitly
   (`tests/contracts/test_specs.py`, vector `system-spec/invalid/retries-refusals`). Golden
   G-30 and G-37 score a refusal as a refusal, not a miss. No account rotation. If cyber
   safeguards block legitimate fixture work, apply to the Cyber Verification Program
   rather than work around them.
3. **Evaluation only, never training.** Transcripts, scores, labels and rubrics may not be
   used to train models, or handed to anyone who would. Fixtures and transcripts carry
   canaries; the dataset card says so (#60).
4. **API keys, not consumer subscriptions.** Claude Code runs on an Anthropic API key under
   the Commercial Terms (`spikes/inspect_day2/live.py` reads `ANTHROPIC_API_KEY`). Do not
   authenticate it through a consumer plan.
5. **Review before publishing, and label AI output.** Published transcripts and excerpts
   are reviewed by a person, attributed to the project, and labeled as AI-generated.
6. **No logos, no implied endorsement.** Name models precisely (exact model IDs).
7. **Before any OpenAI use:** get the Output-as-Confidential-Information clause read for
   transcript publication. Avoid "unsolicited safety testing" framing, and report security
   issues through OpenAI's Coordinated Vulnerability Disclosure Program.
