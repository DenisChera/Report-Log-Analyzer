import { useState } from "react";

function StepRow({ step }) {
  const color =
    step.result === "PASS"
      ? "text-green-700 bg-green-50"
      : step.result === "FAIL"
      ? "text-red-700 bg-red-50"
      : "text-gray-500 bg-gray-50";

  return (
    <tr className="border-b border-gray-100">
      <td className="py-2 px-3 text-sm text-gray-700 font-mono">
        {step.step_name}
      </td>
      <td className="py-2 px-3 text-sm text-gray-600">{step.description}</td>
      <td className={`py-2 px-3 text-sm font-semibold text-center rounded ${color}`}>
        {step.result}
      </td>
    </tr>
  );
}

function TestCaseCard({ tc }) {
  const [expanded, setExpanded] = useState(false);
  const isPass = tc.result === "PASS";

  return (
    <div className="bg-white rounded-xl shadow mb-4 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${
                isPass ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="font-semibold text-gray-800">{tc.test_name}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                isPass
                  ? "bg-green-100 text-green-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              {tc.result}
            </span>
          </div>
          <span className="text-gray-400 text-sm">
            {tc.steps.length} steps {expanded ? "▲" : "▼"}
          </span>
        </div>
        <p className="text-sm text-gray-500 mt-1 ml-6">{tc.module}</p>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          {tc.error_message && (
            <div className="mt-3 bg-red-50 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-red-600 uppercase mb-1">
                Error
              </h4>
              <p className="text-sm text-red-700">{tc.error_message}</p>
            </div>
          )}
          {tc.traceback && (
            <div className="mt-3 bg-gray-900 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">
                Traceback
              </h4>
              <pre className="text-xs text-green-400 whitespace-pre-wrap">
                {tc.traceback}
              </pre>
            </div>
          )}
          <table className="w-full mt-3">
            <thead>
              <tr className="text-xs text-gray-500 uppercase border-b">
                <th className="text-left py-2 px-3">Step</th>
                <th className="text-left py-2 px-3">Description</th>
                <th className="text-center py-2 px-3 w-20">Result</th>
              </tr>
            </thead>
            <tbody>
              {tc.steps.map((s, i) => (
                <StepRow key={i} step={s} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ParsedView({ testCases }) {
  if (!testCases || testCases.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">No test cases found.</div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold text-gray-800 mb-3">
        Test Cases ({testCases.length})
      </h2>
      {testCases.map((tc, i) => (
        <TestCaseCard key={i} tc={tc} />
      ))}
    </div>
  );
}
