import { useEffect, useRef } from "react";

const TYPE_ICONS = {
  agent_start: "\u{1F680}",
  agent_thought: "\u{1F4AD}",
  tool_call: "\u{1F310}",
  tool_result: "\u{1F4C4}",
  agent_complete: "\u{2705}",
  task_complete: "\u{1F3C1}",
  flow_complete: "\u{1F389}",
  error: "\u{274C}",
};

export function LiveFeed({ events }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  if (events.length === 0) return null;

  return (
    <div className="w-full max-w-4xl mx-auto mt-6">
      <h2 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
        Live Activity
      </h2>
      <div className="bg-gray-900 rounded-xl p-4 max-h-80 overflow-y-auto font-mono text-sm">
        {events.map((event, i) => {
          const icon = TYPE_ICONS[event.type] || "\u{2022}";
          const time = event.timestamp
            ? new Date(event.timestamp).toLocaleTimeString()
            : "";
          return (
            <div key={i} className="flex gap-2 text-gray-300 py-1">
              <span className="text-gray-500 w-20 flex-shrink-0">{time}</span>
              <span>{icon}</span>
              <span className="text-blue-400 font-semibold min-w-[100px]">
                {event.agent || "System"}
              </span>
              <span className="text-gray-300 break-all">
                {event.message?.slice(0, 200)}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
