"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type VisionMode = "analyze" | "ocr" | "screenshot" | "chart";

interface ImageAnalyzerProps {
  userId: string;
  fileId: string;
}

interface VisionAnalysisResponse {
  file_id: string;
  result: string;
}

const MODES: { value: VisionMode; label: string }[] = [
  { value: "analyze", label: "Describe" },
  { value: "ocr", label: "OCR" },
  { value: "screenshot", label: "Screenshot" },
  { value: "chart", label: "Chart" },
];

export function ImageAnalyzer({ userId, fileId }: ImageAnalyzerProps) {
  const [mode, setMode] = useState<VisionMode>("analyze");
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const path = `/vision/${mode}/${fileId}`;
      const isOcr = mode === "ocr";
      const body = isOcr
        ? undefined
        : JSON.stringify(mode === "analyze" ? { prompt: prompt || undefined } : { question: prompt || undefined });

      const response = await apiFetch<VisionAnalysisResponse>(path, {
        method: "POST",
        headers: isOcr ? undefined : { "Content-Type": "application/json" },
        body,
        userId,
      });
      setResult(response.result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div className="flex gap-1 rounded-md bg-secondary p-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => setMode(m.value)}
            className={cn(
              "flex-1 rounded-sm px-2 py-1.5 text-xs font-medium transition-colors",
              mode === m.value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode !== "ocr" && (
        <input
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Optional: ask a specific question about the image"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      )}

      <button
        onClick={runAnalysis}
        disabled={isLoading}
        className="self-start rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
      >
        {isLoading ? "Analyzing…" : "Analyze image"}
      </button>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {result && <p className="whitespace-pre-wrap text-sm text-foreground">{result}</p>}
    </div>
  );
}
