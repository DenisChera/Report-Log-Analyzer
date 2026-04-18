import logging
from typing import List

from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import settings
from app.models import AnalysisResult, ParsedReport
from app.parsers.registry import get_parser, UnsupportedFormatError
from app.analyzer import analyze_report
from app.pdf_export import generate_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MTS Report Analyzer",
    description="AI-powered test failure analysis for MTS Application reports",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/parse", response_model=ParsedReport)
async def parse_report(file: UploadFile):
    """Parse an uploaded report file without LLM analysis.
    Useful for previewing parsed data before running full analysis."""
    content = await file.read()
    _check_upload_size(content)

    try:
        parser = get_parser(file.filename or "unknown", content)
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=415, detail=str(e))

    return parser.parse(file.filename or "unknown", content)


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile):
    """Upload a report file → parse → LLM analysis → structured results."""
    content = await file.read()
    _check_upload_size(content)

    try:
        parser = get_parser(file.filename or "unknown", content)
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=415, detail=str(e))

    report = parser.parse(file.filename or "unknown", content)

    if not settings.llm_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured. Set MTS_LLM_API_KEY environment variable.",
        )

    try:
        return await analyze_report(report)
    except Exception as e:
        logger.exception("LLM analysis failed")
        raise HTTPException(status_code=502, detail=f"LLM analysis failed: {e}")


# ─── Batch endpoints ──────────────────────────────────────


async def _parse_one(file: UploadFile) -> dict:
    """Parse a single file, returning a result dict with status."""
    content = await file.read()
    filename = file.filename or "unknown"
    try:
        _check_upload_size(content)
        parser = get_parser(filename, content)
        report = parser.parse(filename, content)
        return {"filename": filename, "status": "ok", "data": report.model_dump()}
    except Exception as e:
        return {"filename": filename, "status": "error", "error": str(e)}


@app.post("/parse/batch")
async def parse_batch(files: List[UploadFile]):
    """Parse multiple report files at once."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    results = []
    for f in files:
        results.append(await _parse_one(f))
    return results


@app.post("/analyze/batch")
async def analyze_batch(files: List[UploadFile]):
    """Parse and analyze multiple report files at once."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if not settings.llm_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured. Set MTS_LLM_API_KEY environment variable.",
        )

    results = []
    for f in files:
        content = await f.read()
        filename = f.filename or "unknown"
        try:
            _check_upload_size(content)
            parser = get_parser(filename, content)
            report = parser.parse(filename, content)
            analysis = await analyze_report(report)
            results.append({"filename": filename, "status": "ok", "data": analysis.model_dump()})
        except Exception as e:
            logger.exception("Analysis failed for %s", filename)
            results.append({"filename": filename, "status": "error", "error": str(e)})
    return results


@app.post("/export/pdf")
async def export_pdf(request: Request):
    """Generate a PDF summary from analysis results.

    Expects JSON body: [{filename, data (AnalysisResult dict)}, ...]
    """
    try:
        reports = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(reports, list) or not reports:
        raise HTTPException(status_code=400, detail="Expected a non-empty array of reports")

    try:
        pdf_bytes = generate_pdf(reports)
    except Exception as e:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=analysis_summary.pdf"},
    )


def _check_upload_size(content: bytes):
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb} MB",
        )
