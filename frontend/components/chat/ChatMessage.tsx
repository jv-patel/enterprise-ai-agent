import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  agentName?: string;
}

export function ChatMessage({ role, content, agentName }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
        )}
      >
        {!isUser && agentName && (
          <div className="mb-1 text-xs font-medium capitalize text-muted-foreground">
            {agentName.replace(/_/g, " ")}
          </div>
        )}
        {content}
      </div>
    </div>
  );
}
