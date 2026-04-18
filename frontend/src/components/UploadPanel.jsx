import { useState, useCallback } from "react";

export default function UploadPanel({ onFilesSelected, isLoading }) {
  const [dragActive, setDragActive] = useState(false);
  const [fileNames, setFileNames] = useState([]);

  const handleFiles = useCallback(
    (files) => {
      if (files && files.length > 0) {
        const arr = Array.from(files);
        setFileNames(arr.map((f) => f.name));
        onFilesSelected(arr);
      }
    },
    [onFilesSelected]
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragActive(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => setDragActive(false);

  const handleInputChange = (e) => {
    handleFiles(e.target.files);
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`border-2 border-dashed rounded-2xl p-12 text-center transition-colors cursor-pointer
        ${dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:border-gray-400"}`}
    >
      <input
        type="file"
        id="file-upload"
        className="hidden"
        onChange={handleInputChange}
        accept=".html,.htm,.xml,.json,.csv"
        disabled={isLoading}
        multiple
      />
      <label htmlFor="file-upload" className="cursor-pointer">
        <div className="text-5xl mb-4">📄</div>
        {isLoading ? (
          <>
            <p className="text-lg font-semibold text-blue-600">Analyzing...</p>
            <p className="text-sm text-gray-500 mt-1">
              Parsing report(s) and running analysis
            </p>
            <div className="mt-4 flex justify-center">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          </>
        ) : fileNames.length > 0 ? (
          <>
            <p className="text-lg font-semibold text-gray-700">
              {fileNames.length === 1 ? fileNames[0] : `${fileNames.length} files selected`}
            </p>
            {fileNames.length > 1 && (
              <p className="text-xs text-gray-400 mt-1">{fileNames.join(", ")}</p>
            )}
            <p className="text-sm text-gray-500 mt-1">
              Drop more files or click to replace
            </p>
          </>
        ) : (
          <>
            <p className="text-lg font-semibold text-gray-700">
              Drop your test report(s) here
            </p>
            <p className="text-sm text-gray-500 mt-1">
              or click to browse — supports multiple files (HTML, XML, JSON, CSV)
            </p>
          </>
        )}
      </label>
    </div>
  );
}
