import { AuthProvider, useAuth } from "./context/AuthContext";
import { LoginPage } from "./components/LoginPage";
import { Loader2, LogOut } from "lucide-react";

function AppContent() {
  const { user, loading, signOut } = useAuth();

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

  // Placeholder — replaced in Phase 8 with full UI
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900">
          🔬 Research Report Generator
        </h1>
        <p className="text-gray-500 mt-2">
          Logged in as {user.email}
        </p>
        <button
          onClick={signOut}
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-gray-500
                     hover:text-gray-700 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
