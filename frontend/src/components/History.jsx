import { useEffect, useState } from "react";
import api from "../lib/api";
import { FileText, Clock } from "lucide-react";

export function History({ onSelect }) {
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    api.get("/api/reports/history").then((res) => setJobs(res.data));
  }, []);

  if (jobs.length === 0) return null;

  return (
    <div className="w-full max-w-4xl mx-auto mt-10">
      <h2 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
        Past Reports
      </h2>
      <div className="space-y-2">
        {jobs.map((job) => (
          <button
            key={job.job_id}
            onClick={() => onSelect(job.job_id)}
            className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border
                       hover:bg-gray-50 transition-colors text-left"
          >
            <FileText className="w-4 h-4 text-gray-400" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">{job.topic}</p>
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(job.created_at).toLocaleString()}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                job.status === "done"
                  ? "bg-green-100 text-green-700"
                  : job.status === "error"
                    ? "bg-red-100 text-red-700"
                    : "bg-blue-100 text-blue-700"
              }`}
            >
              {job.status}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
