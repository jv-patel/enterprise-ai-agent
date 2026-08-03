"use client";

import { VolumeX } from "lucide-react";
import { useVoiceStore } from "@/store/voice-store";

export function StopSpeakingButton() {
  const isSpeaking = useVoiceStore((s) => s.isSpeaking);
  const stopSpeaking = useVoiceStore((s) => s.stopSpeaking);

  if (!isSpeaking) return null;

  return (
    <button
      onClick={stopSpeaking}
      className="flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
    >
      <VolumeX className="h-4 w-4" />
      Stop speaking
    </button>
  );
}
