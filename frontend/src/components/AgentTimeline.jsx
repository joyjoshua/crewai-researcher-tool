import { AgentCard } from "./AgentCard";

const AGENTS = [
  { key: "Research Planner", name: "Planner", emoji: "\u{1F5C2}\u{FE0F}" },
  { key: "Senior Research Specialist", name: "Researcher", emoji: "\u{1F50D}" },
  { key: "Data Analyst & Synthesizer", name: "Analyst", emoji: "\u{1F4CA}" },
  { key: "Technical Report Writer", name: "Writer", emoji: "\u{270D}\u{FE0F}" },
  { key: "Senior Editor & Fact Checker", name: "Editor", emoji: "\u{2705}" },
];

function getAgentStatuses(events) {
  const statuses = {};
  AGENTS.forEach((a) => {
    statuses[a.key] = { status: "idle", steps: 0 };
  });

  events.forEach((event) => {
    const agentKey = event.agent;
    if (!agentKey || !statuses[agentKey]) return;

    if (event.type === "task_complete") {
      statuses[agentKey].status = "done";
    } else if (event.type === "error") {
      statuses[agentKey].status = "error";
    } else {
      if (statuses[agentKey].status !== "done") {
        statuses[agentKey].status = "running";
      }
      statuses[agentKey].steps += 1;
    }
  });

  return statuses;
}

export function AgentTimeline({ events }) {
  const statuses = getAgentStatuses(events);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 w-full max-w-4xl mx-auto">
      {AGENTS.map((agent) => (
        <AgentCard
          key={agent.key}
          name={agent.name}
          emoji={agent.emoji}
          status={statuses[agent.key]?.status}
          stepCount={statuses[agent.key]?.steps}
        />
      ))}
    </div>
  );
}
