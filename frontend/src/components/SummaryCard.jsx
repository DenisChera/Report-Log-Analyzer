export default function SummaryCard({ total, passed, failed, summary }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div className="bg-white rounded-xl shadow p-6 text-center">
        <p className="text-3xl font-bold text-gray-800">{total}</p>
        <p className="text-sm text-gray-500 mt-1">Total Tests</p>
      </div>
      <div className="bg-white rounded-xl shadow p-6 text-center">
        <p className="text-3xl font-bold text-green-600">{passed}</p>
        <p className="text-sm text-gray-500 mt-1">Passed</p>
      </div>
      <div className="bg-white rounded-xl shadow p-6 text-center">
        <p className="text-3xl font-bold text-red-600">{failed}</p>
        <p className="text-sm text-gray-500 mt-1">Failed</p>
      </div>
      {summary && (
        <div className="md:col-span-3 bg-white rounded-xl shadow p-6">
          <h3 className="font-semibold text-gray-700 mb-2">AI Summary</h3>
          <p className="text-gray-600">{summary}</p>
        </div>
      )}
    </div>
  );
}
