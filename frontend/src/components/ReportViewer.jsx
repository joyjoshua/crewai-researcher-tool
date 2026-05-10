import ReactMarkdown from "react-markdown";
import { Download, Copy, CheckCircle2 } from "lucide-react";
import { useState } from "react";

export function ReportViewer({ report }) {
  const [copied, setCopied] = useState(false);

  if (!report) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "research-report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-4xl mx-auto mt-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Final Report</h2>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg
                       hover:bg-gray-50 transition-colors"
          >
            {copied ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg
                       hover:bg-gray-50 transition-colors"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>
      </div>
      <div className="prose prose-sm max-w-none bg-white rounded-xl border p-8">
        <ReactMarkdown>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
