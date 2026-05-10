import { CheckCircle2, Loader2, Clock, AlertCircle } from "lucide-react";

const STATUS_CONFIG = {
  idle: { icon: Clock, color: "text-gray-400", bg: "bg-gray-50", label: "Waiting" },
  running: { icon: Loader2, color: "text-blue-500", bg: "bg-blue-50", label: "Running" },
  done: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-50", label: "Done" },
  error: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50", label: "Error" },
};

export function AgentCard({ name, emoji, status = "idle", stepCount = 0 }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.idle;
  const Icon = config.icon;

  return (
    <div className={`rounded-xl border p-4 ${config.bg} transition-all duration-300`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-lg">{emoji}</span>
        <Icon
          className={`w-5 h-5 ${config.color} ${status === "running" ? "animate-spin" : ""}`}
        />
      </div>
      <h3 className="font-semibold text-gray-900 text-sm">{name}</h3>
      <p className={`text-xs mt-1 ${config.color}`}>{config.label}</p>
      {stepCount > 0 && (
        <p className="text-xs text-gray-500 mt-1">{stepCount} steps</p>
      )}
    </div>
  );
}
