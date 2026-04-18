import asyncio
import json
import logging

import httpx

from app.config import settings
from app.models import AnalysisResult, ParsedReport

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert QA engineer analyzing test results for the MTS Application, \
an automotive testing tool. You will receive structured test failure data and must \
produce a JSON analysis.

APPLICATION CONTEXT:
- MTS Application: automotive signal analysis and recording tool
- Test environment: Windows desktop, CANoe integration, Ethernet/CAN bus
- Test framework: Python automation with pywinauto

RULES:
- Return ONLY valid JSON matching the schema below. No markdown, no extra text.
- failure_type must be one of: "environment", "bug", "broken_test"
- severity must be one of: "critical", "medium", "minor"
- Be specific in root_cause — reference the actual error message.
- For patterns, group tests that share the same underlying issue.
- top_priority: the single most important thing to fix first.

RESPONSE SCHEMA:
{
  "run_summary": "string — 2-3 sentence overall summary",
  "test_analyses": [
    {
      "test_name": "string",
      "module": "string",
      "result": "FAIL",
      "root_cause": "string — plain language explanation",
      "failure_type": "environment | bug | broken_test",
      "severity": "critical | medium | minor",
      "recommendation": "string — actionable next step"
    }
  ],
  "patterns": [
    {
      "pattern_title": "string — short pattern name",
      "affected_tests": ["test_name_1", "test_name_2"],
      "explanation": "string — why these are grouped"
    }
  ],
  "top_priority": "string — what to fix first"
}\
"""


def _build_user_prompt(report: ParsedReport) -> str:
    lines = [
        f"Report: {report.source_filename}",
        f"Total tests: {report.total_tests} | Passed: {report.passed} | Failed: {report.failed}",
        "",
        "FAILED TESTS:",
    ]
    for tc in report.test_cases:
        if tc.result != "FAIL":
            continue
        step_names = [s.step_name for s in tc.steps]
        fail_steps = [s for s in tc.steps if s.result == "FAIL"]
        last_pass = ""
        for s in reversed(tc.steps):
            if s.result == "PASS":
                last_pass = s.step_name
                break

        lines.append(f"\n  Test: {tc.test_name}")
        lines.append(f"  Module: {tc.module}")
        lines.append(f"  Total steps: {len(tc.steps)}")
        lines.append(f"  Last passing step: {last_pass}")
        if tc.error_message:
            lines.append(f"  Error message: {tc.error_message}")
        if tc.traceback:
            lines.append(f"  Traceback:\n    {tc.traceback}")

    lines.append("\nAnalyze these failures and return JSON matching the schema.")
    return "\n".join(lines)


async def _call_anthropic(system: str, user_msg: str) -> str:
    async with httpx.AsyncClient(timeout=120, verify=False) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": 4096,
                "system": system,
                "messages": [{"role": "user", "content": user_msg}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _call_openai(system: str, user_msg: str) -> str:
    async with httpx.AsyncClient(timeout=120, verify=False) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_gemini(system: str, user_msg: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.llm_model}:generateContent?key={settings.llm_api_key}"
    )
    async with httpx.AsyncClient(timeout=120, verify=False) as client:
        resp = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": user_msg}]}],
                "generationConfig": {"temperature": 0.2},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


OPENROUTER_FALLBACK_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
]


async def _call_openrouter(system: str, user_msg: str) -> str:
    models_to_try = [settings.llm_model] + [
        m for m in OPENROUTER_FALLBACK_MODELS if m != settings.llm_model
    ]
    async with httpx.AsyncClient(timeout=300, verify=False) as client:
        last_error = None
        for model in models_to_try:
            logger.info("Trying model %s", model)
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                    "X-OpenRouter-Title": "MTS Report Analyzer",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.2,
                },
            )
            if resp.status_code == 429:
                logger.warning("Model %s rate-limited, trying next", model)
                last_error = resp
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        # All models failed
        if last_error:
            last_error.raise_for_status()
        raise RuntimeError("All OpenRouter models returned 429")


def _parse_llm_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove ```json ... ``` wrapper
        lines = text.split("\n")
        lines = lines[1:]  # drop opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


async def analyze_report(report: ParsedReport) -> AnalysisResult:
    """Send parsed report to LLM and return structured analysis."""
    if report.failed == 0:
        return AnalysisResult(
            total_tests=report.total_tests,
            passed=report.passed,
            failed=0,
            run_summary="All tests passed. No failures to analyze.",
            test_analyses=[],
            patterns=[],
            top_priority="No action needed — all tests passed.",
        )

    user_prompt = _build_user_prompt(report)
    logger.info("Sending %d failed test(s) to %s for analysis", report.failed, settings.llm_provider)

    if settings.llm_provider == "anthropic":
        raw = await _call_anthropic(SYSTEM_PROMPT, user_prompt)
    elif settings.llm_provider == "openai":
        raw = await _call_openai(SYSTEM_PROMPT, user_prompt)
    elif settings.llm_provider == "gemini":
        raw = await _call_gemini(SYSTEM_PROMPT, user_prompt)
    elif settings.llm_provider == "openrouter":
        raw = await _call_openrouter(SYSTEM_PROMPT, user_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    llm_data = _parse_llm_json(raw)

    return AnalysisResult(
        total_tests=report.total_tests,
        passed=report.passed,
        failed=report.failed,
        run_summary=llm_data.get("run_summary", ""),
        test_analyses=llm_data.get("test_analyses", []),
        patterns=llm_data.get("patterns", []),
        top_priority=llm_data.get("top_priority", ""),
    )
