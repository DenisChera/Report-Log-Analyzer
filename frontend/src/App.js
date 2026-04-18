import { useState, useCallback } from "react";
import UploadPanel from "./components/UploadPanel";
import SummaryCard from "./components/SummaryCard";
import TestResultList from "./components/TestResultList";
import PatternInsights from "./components/PatternInsights";
import ParsedView from "./components/ParsedView";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function App() {
  // reports: [{filename, fileObj, parsed, analysis, analyzing, analyzeError}]
  const [reports, setReports] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // ─── Upload & Parse ──────────────────────────────────────
  const handleFilesSelected = async (files) => {
    setError(null);
    setIsLoading(true);
    setReports([]);

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    try {
      const resp = await fetch(`${API_URL}/parse/batch`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `Server error: ${resp.status}`);
      }
      const data = await resp.json();

      // Map each result to a report object, keeping the File reference
      const mapped = data.map((item, i) => ({
        filename: item.filename,
        fileObj: files[i],
        parsed: item.status === "ok" ? item.data : null,
        parseError: item.status === "error" ? item.error : null,
        analysis: null,
        analyzing: false,
        analyzeError: null,
      }));
      setReports(mapped);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Analyze one report ──────────────────────────────────
  const analyzeOne = useCallback(async (index) => {
    setReports((prev) =>
      prev.map((r, i) =>
        i === index ? { ...r, analyzing: true, analyzeError: null } : r
      )
    );

    const report = reports[index];
    const formData = new FormData();
    formData.append("file", report.fileObj);

    try {
      const resp = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `Server error: ${resp.status}`);
      }
      const data = await resp.json();
      setReports((prev) =>
        prev.map((r, i) =>
          i === index ? { ...r, analysis: data, analyzing: false } : r
        )
      );
    } catch (err) {
      setReports((prev) =>
        prev.map((r, i) =>
          i === index ? { ...r, analyzeError: err.message, analyzing: false } : r
        )
      );
    }
  }, [reports]);

  // ─── Analyze all failed ──────────────────────────────────
  const analyzeAllFailed = useCallback(async () => {
    const failedIndices = reports
      .map((r, i) => (r.parsed && r.parsed.failed > 0 && !r.analysis ? i : -1))
      .filter((i) => i >= 0);

    for (const idx of failedIndices) {
      await analyzeOne(idx);
    }
  }, [reports, analyzeOne]);

  // ─── Computed values ─────────────────────────────────────
  const parsedReports = reports.filter((r) => r.parsed);
  const totalTests = parsedReports.reduce((s, r) => s + r.parsed.total_tests, 0);
  const totalPassed = parsedReports.reduce((s, r) => s + r.parsed.passed, 0);
  const totalFailed = parsedReports.reduce((s, r) => s + r.parsed.failed, 0);
  const failedWithoutAnalysis = reports.filter(
    (r) => r.parsed && r.parsed.failed > 0 && !r.analysis
  );
  const anyAnalyzing = reports.some((r) => r.analyzing);
  const analyzedReports = reports.filter((r) => r.analysis);
  const [exporting, setExporting] = useState(false);

  // ─── Export PDF ──────────────────────────────────────────
  const exportPdf = useCallback(async () => {
    const toExport = analyzedReports.map((r) => ({
      filename: r.filename,
      data: r.analysis,
    }));
    setExporting(true);
    try {
      const resp = await fetch(`${API_URL}/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toExport),
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}));
        throw new Error(d.detail || "PDF export failed");
      }
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analysis_summary_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }, [analyzedReports]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-800">
            MTS Report Analyzer
          </h1>
          <p className="text-sm text-gray-500">
            AI-powered test failure analysis
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <UploadPanel onFilesSelected={handleFilesSelected} isLoading={isLoading} />

        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {parsedReports.length > 0 && (
          <div className="mt-8">
            {/* Aggregate summary */}
            <SummaryCard total={totalTests} passed={totalPassed} failed={totalFailed} />

            {/* Action buttons */}
            <div className="mt-4 mb-6 flex items-center gap-3 flex-wrap">
              {failedWithoutAnalysis.length > 0 && (
                <button
                  onClick={analyzeAllFailed}
                  disabled={anyAnalyzing}
                  className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg font-medium
                    hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                    transition-colors flex items-center gap-2"
                >
                  {anyAnalyzing ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>🤖 Analyze All Failed ({failedWithoutAnalysis.length} reports)</>
                  )}
                </button>
              )}

              {analyzedReports.length > 0 && (
                <button
                  onClick={exportPdf}
                  disabled={exporting}
                  className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium
                    hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed
                    transition-colors flex items-center gap-2"
                >
                  {exporting ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>📥 Download PDF ({analyzedReports.length} reports)</>
                  )}
                </button>
              )}

              {failedWithoutAnalysis.length > 0 && (
                <span className="text-sm text-gray-500">
                  Uses 1 LLM request per report
                </span>
              )}
            </div>

            {/* Parse errors */}
            {reports.filter((r) => r.parseError).map((r, i) => (
              <div key={`perr-${i}`} className="mb-4 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
                <strong>{r.filename}:</strong> {r.parseError}
              </div>
            ))}

            {/* Individual reports */}
            {parsedReports.map((r, i) => {
              const globalIndex = reports.indexOf(r);
              const hasFails = r.parsed.failed > 0;

              return (
                <div key={i} className="mb-8 bg-white rounded-xl shadow overflow-hidden">
                  {/* Report header */}
                  <div className="px-5 py-4 border-b bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">📄</span>
                      <div>
                        <h2 className="font-semibold text-gray-800">{r.filename}</h2>
                        <p className="text-sm text-gray-500">
                          {r.parsed.total_tests} tests —{" "}
                          <span className="text-green-600">{r.parsed.passed} passed</span>
                          {r.parsed.failed > 0 && (
                            <>, <span className="text-red-600">{r.parsed.failed} failed</span></>
                          )}
                        </p>
                      </div>
                    </div>

                    {/* Per-report Analyze button */}
                    {hasFails && !r.analysis && (
                      <button
                        onClick={() => analyzeOne(globalIndex)}
                        disabled={r.analyzing || anyAnalyzing}
                        className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg font-medium
                          hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                          transition-colors flex items-center gap-2"
                      >
                        {r.analyzing ? (
                          <>
                            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>🤖 Analyze</>
                        )}
                      </button>
                    )}
                    {r.analysis && (
                      <span className="text-sm text-green-600 font-medium">✓ Analyzed</span>
                    )}
                  </div>

                  {/* Report content */}
                  <div className="p-5">
                    {/* Analyze error */}
                    {r.analyzeError && (
                      <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                        <strong>Analysis error:</strong> {r.analyzeError}
                      </div>
                    )}

                    {/* AI Analysis results */}
                    {r.analysis && (
                      <div className="mb-6">
                        {r.analysis.run_summary && (
                          <p className="text-sm text-gray-600 mb-3 italic">
                            {r.analysis.run_summary}
                          </p>
                        )}
                        {r.analysis.top_priority && (
                          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
                            <h3 className="font-semibold text-blue-800">🎯 Top Priority</h3>
                            <p className="text-blue-700 mt-1">{r.analysis.top_priority}</p>
                          </div>
                        )}
                        <PatternInsights patterns={r.analysis.patterns} />
                        <TestResultList analyses={r.analysis.test_analyses} />
                      </div>
                    )}

                    {/* Parsed test cases (always shown) */}
                    <ParsedView testCases={r.parsed.test_cases} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
