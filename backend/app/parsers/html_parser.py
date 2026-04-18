from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.models import ParsedReport, ParsedTestCase, TestStep
from app.parsers.base import BaseParser

_TESTCASE_RE = re.compile(r"test_?case_\d+", re.IGNORECASE)
_INFRA_PREFIXES = ("structure", "mats_utils", "BaseTestCase", "test_suites")


class MtsHtmlParser(BaseParser):
    """Parser for MTS Application HTML test reports.

    Report structure:
      - Single <table class="test-result-table"> with 4 columns:
        Test Case | Test Step | Description | Result
      - Each row is <tr class="test-result-step-row">
      - Result cell CSS class determines status:
        * test-result-step-result-cell-ok       → PASS
        * test-result-step-result-cell-failure   → FAIL
        * test-result-step-result-cell-not-performed → NOT_PERFORMED
      - Verdict rows have format 'Module/TestName', no '.py', and are not
        infrastructure steps (structure.*, BaseTestCase/*, etc.).
      - Intermediate test steps reference the .py file path, e.g.
        "test_suites\\L3_AudioSpec.py/test_case_211_..."
      - Some test cases may not have a verdict row (e.g. crashed mid-exec).
    """

    def can_parse(self, filename: str, content: bytes) -> bool:
        if not filename.lower().endswith((".html", ".htm")):
            return False
        try:
            text = content.decode("utf-8", errors="ignore")
            return "test-result-table" in text
        except Exception:
            return False

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_verdict(step_name: str) -> bool:
        """True if this row is a final verdict (Module/TestName, no .py)."""
        if ".py" in step_name:
            return False
        if "/" not in step_name:
            return False
        parts = step_name.split("/", 1)
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""
        if not left or not right:
            return False
        if any(left.startswith(p) for p in _INFRA_PREFIXES):
            return False
        return True

    @staticmethod
    def _tc_key(step_name: str) -> str | None:
        """Return a canonical key identifying the test case, or None."""
        if "/" not in step_name:
            return None
        after = step_name.rsplit("/", 1)[1].strip()
        if not after:
            return None
        if ".py" in step_name:
            # Intermediate row — must contain a recognisable tc pattern
            if _TESTCASE_RE.search(after):
                return after
            return None
        # Non-.py row — check if it's a verdict
        left = step_name.split("/", 1)[0].strip()
        if not left or any(left.startswith(p) for p in _INFRA_PREFIXES):
            return None
        return after

    @staticmethod
    def _classify_result(result_cell) -> str:
        css_classes = result_cell.get("class", [])
        for cls in css_classes:
            if "cell-ok" in cls:
                return "PASS"
            if "cell-failure" in cls:
                return "FAIL"
            if "not-performed" in cls:
                return "NOT_PERFORMED"
        text = result_cell.get_text(strip=True).upper()
        if text in ("PASS", "FAIL", "NOT_PERFORMED"):
            return text
        return "UNKNOWN"

    @staticmethod
    def _extract_identity(step_name: str) -> tuple[str, str]:
        """Extract (test_name, module) from a step name.

        Works for both verdict and intermediate formats:
          'L3_Spec/test_case_211_Audio'         → ('test_case_211_Audio', 'L3_Spec')
          'test_suites\\L3_Spec.py/test_case_X' → ('test_case_X', 'L3_Spec')
          'VehicleBus/VehBusTests'              → ('VehBusTests', 'VehicleBus')
        """
        if "/" in step_name:
            left, right = step_name.rsplit("/", 1)
            test_name = right.strip()
            module = left.replace("\\", "/").strip()
            module = re.sub(r"^test_suites[/\\]?", "", module)
            module = re.sub(r"\.py$", "", module)
            return test_name, module
        return step_name.strip(), "unknown_module"

    # ------------------------------------------------------------------
    # main parse
    # ------------------------------------------------------------------
    def parse(self, filename: str, content: bytes) -> ParsedReport:
        soup = BeautifulSoup(content, "html.parser")
        table = soup.find("table", class_="test-result-table")
        if not table:
            raise ValueError("No test-result-table found in HTML report")

        rows = table.find("tbody").find_all("tr", class_="test-result-step-row")
        if not rows:
            raise ValueError("No test step rows found in report")

        # ---- collect raw step data ----
        raw_steps: list[dict] = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            step_name = cells[1].get_text(strip=True)
            description = cells[2].get_text(strip=True)
            traceback_text = None
            if step_name.lower() == "traceback":
                traceback_text = cells[2].get_text(separator="\n", strip=True)
            result = self._classify_result(cells[3])
            is_verdict = self._is_verdict(step_name)
            raw_steps.append({
                "step_name": step_name,
                "description": description,
                "result": result,
                "is_verdict": is_verdict,
                "traceback": traceback_text,
                "tc_key": self._tc_key(step_name),
            })

        # ---- group rows into test cases ----
        # A new group starts when:
        #   - a tc_key appears that differs from the current one, OR
        #   - a verdict row finalises the current group.
        # Rows before the first detected tc_key/verdict are attached to the
        # first group once one starts.
        tc_groups: list[dict] = []
        cur: dict | None = None
        pending: list[dict] = []  # rows before first tc detected

        for s in raw_steps:
            key = s["tc_key"]

            if key and cur is not None and key != cur["tc_key"]:
                # Changing to a different test case — finalise previous
                tc_groups.append(cur)
                cur = None

            if cur is None and key:
                # Start a new group (prepend any pending infra rows)
                cur = {"tc_key": key, "raw": list(pending), "verdict_step": None}
                pending = []

            if cur is None:
                pending.append(s)
                continue

            cur["raw"].append(s)

            if s["is_verdict"]:
                cur["verdict_step"] = s
                tc_groups.append(cur)
                cur = None

        # Leftover
        if cur is not None:
            tc_groups.append(cur)

        # ---- build ParsedTestCase objects ----
        test_cases: list[ParsedTestCase] = []
        for g in tc_groups:
            # Identity: prefer verdict row, fall back to first intermediate
            identity_step = g["verdict_step"]["step_name"] if g["verdict_step"] else None
            if not identity_step:
                for s in g["raw"]:
                    if s["tc_key"]:
                        identity_step = s["step_name"]
                        break
            if not identity_step:
                continue
            test_name, module = self._extract_identity(identity_step)

            # Result: prefer verdict, else derive from steps
            if g["verdict_step"]:
                final_result = g["verdict_step"]["result"]
            else:
                has_fail = any(s["result"] == "FAIL" for s in g["raw"])
                final_result = "FAIL" if has_fail else "PASS"

            steps: list[TestStep] = []
            error_messages: list[str] = []
            traceback_text: str | None = None

            for s in g["raw"]:
                if s["traceback"]:
                    traceback_text = s["traceback"]
                    continue
                steps.append(TestStep(
                    step_name=s["step_name"],
                    description=s["description"],
                    result=s["result"],
                ))
                if s["result"] == "FAIL" and not s["is_verdict"]:
                    error_messages.append(s["description"])

            test_cases.append(ParsedTestCase(
                test_name=test_name,
                module=module,
                result=final_result,
                steps=steps,
                error_message=" | ".join(error_messages) if error_messages else None,
                traceback=traceback_text,
            ))

        passed = sum(1 for tc in test_cases if tc.result == "PASS")
        failed = sum(1 for tc in test_cases if tc.result == "FAIL")

        return ParsedReport(
            source_filename=filename,
            total_tests=len(test_cases),
            passed=passed,
            failed=failed,
            test_cases=test_cases,
        )
