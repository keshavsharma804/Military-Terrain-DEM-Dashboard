import React, { useState } from "react";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

function ExportButton() {
  const [loading, setLoading] = useState(false);

  const handleExport = () => {
    setLoading(true);
    const exportWindow = window.open("http://localhost:5000/api/export", "_blank");

    // Simulate short delay for feedback
    setTimeout(() => {
      setLoading(false);
      toast.success("Metadata export started!");
    }, 1500);
  };

  return (
    <button
      onClick={handleExport}
      className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700 flex items-center gap-2 transition-all duration-300 disabled:opacity-60"
      disabled={loading}
    >
      {loading ? (
        <svg
          className="animate-spin h-5 w-5 text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v8H4z"
          />
        </svg>
      ) : (
        <span>📥 Export Metadata CSV</span>
      )}
    </button>
  );
}

export default ExportButton;
