"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

interface FileInsightPanelProps {
  userId: string;
  fileId: string;
}

interface FileSummaryResponse {
  file_id: string;
  summary: string;
}

interface FileAnswerResponse {
  file_id: string;
  question: string;
  answer: string;
}

export function FileInsightPanel({ userId, fileId }: FileInsightPanelProps) {
  const [summary, setSummary] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSummarize = async () => {
    setIsSummarizing(true);
    setError(null);
    try {
      const result = await apiFetch<FileSummaryResponse>(`/files/${fileId}/summarize`, {
        method: "POST",
        userId,
      });
      setSummary(result.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not summarize this file.");
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) return;
    setIsAsking(true);
    setError(null);
    try {
      const result = await apiFetch<FileAnswerResponse>(`/files/${fileId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        userId,
      });
      setAnswer(result.answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not answer that question.");
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-2">
        <button
          onClick={handleSummarize}
          disabled={isSummarizing}
          className="self-start rounded-md bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground disabled:opacity-60"
        >
          {isSummarizing ? "Summarizing…" : "Summarize document"}
        </button>
        {summary && <p className="whitespace-pre-wrap text-sm text-foreground">{summary}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && handleAsk()}
            placeholder="Ask a question about this document…"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <button
            onClick={handleAsk}
            disabled={isAsking || !question.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {isAsking ? "Asking…" : "Ask"}
          </button>
        </div>
        {answer && <p className="whitespace-pre-wrap text-sm text-foreground">{answer}</p>}
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
