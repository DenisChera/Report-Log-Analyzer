from pydantic import BaseModel


class TestStep(BaseModel):
    """A single step within a test case execution."""
    step_name: str
    description: str
    result: str  # 'PASS', 'FAIL', 'NOT_PERFORMED', etc.


class ParsedTestCase(BaseModel):
    """A single parsed test case with all its steps and metadata."""
    test_name: str
    module: str
    result: str  # Final verdict: 'PASS' or 'FAIL'
    steps: list[TestStep]
    error_message: str | None = None
    traceback: str | None = None


class ParsedReport(BaseModel):
    """Format-agnostic output of any parser. This is the contract
    between parsers and the rest of the pipeline."""
    source_filename: str
    total_tests: int
    passed: int
    failed: int
    test_cases: list[ParsedTestCase]


# ---------- LLM Analysis Response Models ----------

class TestFailureAnalysis(BaseModel):
    test_name: str
    module: str
    result: str
    root_cause: str
    failure_type: str  # 'environment' | 'bug' | 'broken_test'
    severity: str      # 'critical' | 'medium' | 'minor'
    recommendation: str


class PatternInsight(BaseModel):
    pattern_title: str
    affected_tests: list[str]
    explanation: str


class AnalysisResult(BaseModel):
    total_tests: int
    passed: int
    failed: int
    run_summary: str
    test_analyses: list[TestFailureAnalysis]
    patterns: list[PatternInsight]
    top_priority: str
