"use client";

import { useRef, useState } from "react";
import { Radio, Square } from "lucide-react";
import { StreamingVoiceClient } from "@/lib/voice-stream-client";
import { cn } from "@/lib/utils";

export function StreamingVoiceTranscript() {
  const clientRef = useRef<StreamingVoiceClient | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [interimText, setInterimText] = useState("");
  const [finalText, setFinalText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setError(null);
    setInterimText("");
    setFinalText("");
    clientRef.current = new StreamingVoiceClient();
    try {
      await clientRef.current.start({
        onResult: (result) => {
          if (result.is_final) {
            setFinalText((prev) => (prev ? `${prev} ${result.transcript}` : result.transcript));
            setInterimText("");
          } else {
            setInterimText(result.transcript);
          }
        },
        onError: (message) => setError(message),
        onClose: () => setIsStreaming(false),
      });
      setIsStreaming(true);
    } catch {
      setError("Could not start streaming voice — check microphone permissions.");
    }
  };

  const stop = () => {
    clientRef.current?.stop();
    setIsStreaming(false);
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-3">
        <button
          onClick={isStreaming ? stop : start}
          className={cn(
            "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors",
            isStreaming ? "bg-destructive text-destructive-foreground" : "bg-primary text-primary-foreground"
          )}
        >
          {isStreaming ? <Square className="h-4 w-4" /> : <Radio className="h-4 w-4" />}
          {isStreaming ? "Stop streaming" : "Start live transcription"}
        </button>
        {isStreaming && <span className="text-xs text-muted-foreground">Listening…</span>}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
      <p className="min-h-[3rem] text-sm text-foreground">
        {finalText}
        <span className="text-muted-foreground">{interimText ? ` ${interimText}` : ""}</span>
      </p>
    </div>
  );
}
