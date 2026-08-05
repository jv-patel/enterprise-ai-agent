"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Loader2, Send } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useUser } from "@/contexts/UserContext";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { MicrophoneButton } from "@/components/voice/MicrophoneButton";
import { StopSpeakingButton } from "@/components/voice/StopSpeakingButton";

interface Message {
  role: "user" | "assistant";
  content: string;
  agentName?: string;
}

interface AgentRunResponse {
  run_id: string;
  chat_id: string;
  answer: string;
  status: string;
  agent_name: string;
}

export function ChatWindow() {
  const { userId } = useUser();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [chatId, setChatId] = useState<string | undefined>(undefined);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || !userId) return;

    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setIsSending(true);

    try {
      const result = await apiFetch<AgentRunResponse>("/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, chat_id: chatId }),
        userId,
      });
      setChatId(result.chat_id);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer, agentName: result.agent_name }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void sendMessage(input);
  };

  const handleVoiceExchange = (transcript: string, answer: string, newChatId: string) => {
    setChatId(newChatId);
    setMessages((prev) => [...prev, { role: "user", content: transcript }, { role: "assistant", content: answer }]);
  };

  if (!userId) return null;

  return (
    <div className="mx-auto flex h-screen w-full max-w-2xl flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center px-8 text-center text-sm text-muted-foreground">
            Ask me anything — I can help with email, calendar, notes, tasks, files, and more.
          </div>
        )}
        {messages.map((message, index) => (
          <ChatMessage key={index} role={message.role} content={message.content} agentName={message.agentName} />
        ))}
        {isSending && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-secondary px-4 py-2.5">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <p className="px-4 pb-2 text-center text-sm text-destructive">{error}</p>}

      <div className="flex items-center justify-center gap-3 px-4 pb-2">
        <StopSpeakingButton />
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-border p-4">
        <MicrophoneButton userId={userId} chatId={chatId} onExchange={handleVoiceExchange} />
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Type a message…"
          className="flex-1 rounded-full border border-input bg-background px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
        <button
          type="submit"
          disabled={isSending || !input.trim()}
          aria-label="Send message"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity disabled:opacity-60"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
