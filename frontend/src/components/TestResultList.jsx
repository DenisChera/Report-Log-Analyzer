import { useState } from "react";

const BADGE_COLORS = {
  environment: "bg-amber-100 text-amber-800",
  bug: "bg-red-100 text-red-800",
  broken_test: "bg-purple-100 text-purple-800",
};

const SEVERITY_COLORS = {
  critical: "bg-red-600",
  medium: "bg-yellow-500",
  minor: "bg-gray-400",
};

function FailureCard({ analysis }) {
  const [expanded, setExpanded] = useState(false);
  const badgeClass = BADGE_COLORS[analysis.failure_type] || "bg-gray-100 text-gray-800";
  const severityClass = SEVERITY_COLORS[analysis.severity] || "bg-gray-400";

  return (
    <div className="bg-white rounded-xl shadow mb-3 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${severityClass}`} title={analysis.severity} />
            <span className="font-semibold text-gray-800">{analysis.test_name}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badgeClass}`}>
              {analysis.failure_type}
            </span>
          </div>
          <span className="text-gray-400 text-sm">{expanded ? "▲" : "▼"}</span>
        </div>
        <p className="text-sm text-gray-500 mt-1 ml-6">{analysis.module}</p>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="mt-3 space-y-3">
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase">Root Cause</h4>
              <p className="text-gray-700 mt-1">{analysis.root_cause}</p>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase">Recommendation</h4>
              <p className="text-gray-700 mt-1">{analysis.recommendation}</p>
            </div>
            <div className="flex gap-4 text-sm text-gray-500">
              <span>Severity: <strong className="text-gray-700">{analysis.severity}</strong></span>
              <span>Type: <strong className="text-gray-700">{analysis.failure_type}</strong></span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function TestResultList({ analyses }) {
  if (!analyses || analyses.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No failures to display.
      </div>
    );
  }

  const severityOrder = { critical: 0, medium: 1, minor: 2 };
  const sorted = [...analyses].sort(
    (a, b) => (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3)
  );

  return (
    <div>
      <h2 className="text-lg font-bold text-gray-800 mb-3">
        Failed Tests ({analyses.length})
      </h2>
      {sorted.map((a, i) => (
        <FailureCard key={i} analysis={a} />
      ))}
    </div>
  );
}
