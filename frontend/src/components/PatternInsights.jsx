export default function PatternInsights({ patterns }) {
  if (!patterns || patterns.length === 0) return null;

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold text-gray-800 mb-3">Pattern Insights</h2>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {patterns.map((p, i) => (
          <div
            key={i}
            className="min-w-[300px] bg-white rounded-xl shadow p-5 flex-shrink-0"
          >
            <h3 className="font-semibold text-gray-800 mb-2">{p.pattern_title}</h3>
            <p className="text-sm text-gray-600 mb-3">{p.explanation}</p>
            <div className="flex flex-wrap gap-1">
              {p.affected_tests.map((t, j) => (
                <span
                  key={j}
                  className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
