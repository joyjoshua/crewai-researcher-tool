import { useState, useEffect } from "react";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./hooks/useAuth";
import { LoginPage } from "./components/LoginPage";
import { TopicInput } from "./components/TopicInput";
import { AgentTimeline } from "./components/AgentTimeline";
import { LiveFeed } from "./components/LiveFeed";
import { ReportViewer } from "./components/ReportViewer";
import { History } from "./components/History";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { useAgentStream } from "./hooks/useAgentStream";
import api from "./lib/api";
import { Loader2, LogOut } from "lucide-react";

function Dashboard() {
  const { user, signOut } = useAuth();
  const [jobId, setJobId] = useState(null);
  const [report, setReport] = useState(null);
  const { events, status } = useAgentStream(jobId);

  const isLoading = status === "running";

  const handleSubmit = async (topic) => {
    setReport(null);
    setJobId(null);

    try {
      const res = await api.post("/api/report/generate", { topic });
      setJobId(res.data.job_id);
    } catch (err) {
      console.error("Failed to start job:", err);
    }
  };

  useEffect(() => {
    if (status !== "done" || !jobId || report) return;

    const fetchReport = async () => {
      try {
        const res = await api.get(`/api/report/${jobId}`);
        if (res.data.status === "done") {
          setReport(res.data.report);
        }
      } catch (err) {
        console.error("Failed to fetch report:", err);
      }
    };

    fetchReport();
  }, [status, jobId, report]);

  const handleSelectHistory = async (selectedJobId) => {
    try {
      const res = await api.get(`/api/report/${selectedJobId}`);
      if (res.data.report) {
        setReport(res.data.report);
        setJobId(null);
      }
    } catch (err) {
      console.error("Failed to load report:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900">
          Research Report Generator
        </h1>
        <p className="text-gray-500 mt-2">
          Enter a topic and watch 5 AI agents research, analyse, and write a report
        </p>
        <div className="mt-3 flex items-center justify-center gap-3 text-sm text-gray-400">
          <span>{user.email}</span>
          <button
            onClick={signOut}
            className="inline-flex items-center gap-1 hover:text-gray-600 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </div>

      <TopicInput onSubmit={handleSubmit} isLoading={isLoading} />

      <ErrorBoundary>
        {jobId && (
          <div className="mt-8">
            <AgentTimeline events={events} />
          </div>
        )}

        {jobId && <LiveFeed events={events} />}
      </ErrorBoundary>

      <ErrorBoundary>
        {report && <ReportViewer report={report} />}
      </ErrorBoundary>

      <ErrorBoundary>
        <History onSelect={handleSelectHistory} />
      </ErrorBoundary>
    </div>
  );
}

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <Dashboard />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
