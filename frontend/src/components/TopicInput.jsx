import { useState } from "react";
import { Search, Loader2 } from "lucide-react";

export function TopicInput({ onSubmit, isLoading }) {
  const [topic, setTopic] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (topic.trim() && !isLoading) {
      onSubmit(topic.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a research topic..."
            maxLength={500}
            className="w-full pl-11 pr-4 py-3 rounded-lg border border-gray-300 bg-white
                       text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                       focus:ring-blue-500 focus:border-transparent text-base"
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          disabled={!topic.trim() || isLoading}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium
                     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center gap-2 transition-colors"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running
            </>
          ) : (
            "Research"
          )}
        </button>
      </div>
    </form>
  );
}
