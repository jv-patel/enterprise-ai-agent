"use client";

import { useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { AudioRecorder } from "@/lib/audio-recorder";
import { apiFetch } from "@/lib/api";
import { useVoiceStore } from "@/store/voice-store";
import { cn } from "@/lib/utils";

interface VoiceChatResult {
  run_id: string;
  chat_id: string;
  transcript: string;
  answer: string;
  answer_audio_base64: string;
}

interface MicrophoneButtonProps {
  userId: string;
  chatId?: string;
  onExchange?: (transcript: string, answer: string, chatId: string) => void;
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
  return new Blob([bytes], { type: mimeType });
}

export function MicrophoneButton({ userId, chatId, onExchange }: MicrophoneButtonProps) {
  const recorderRef = useRef<AudioRecorder | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isRecording = useVoiceStore((s) => s.isRecording);
  const isTranscribing = useVoiceStore((s) => s.isTranscribing);
  const setRecording = useVoiceStore((s) => s.setRecording);
  const setTranscribing = useVoiceStore((s) => s.setTranscribing);
  const setSpeaking = useVoiceStore((s) => s.setSpeaking);
  const setCurrentAudio = useVoiceStore((s) => s.setCurrentAudio);
  const setTranscript = useVoiceStore((s) => s.setTranscript);

  const startRecording = async () => {
    setError(null);
    try {
      recorderRef.current = new AudioRecorder();
      await recorderRef.current.start();
      setRecording(true);
    } catch {
      setError("Microphone access was denied or is unavailable.");
    }
  };

  const stopRecordingAndSend = async () => {
    setRecording(false);
    setTranscribing(true);
    try {
      const blob = await recorderRef.current!.stop();
      const formData = new FormData();
      formData.append("file", blob, "recording.webm");
      if (chatId) formData.append("chat_id", chatId);

      const result = await apiFetch<VoiceChatResult>("/voice/chat", {
        method: "POST",
        body: formData,
        userId,
      });

      setTranscript(result.transcript);
      onExchange?.(result.transcript, result.answer, result.chat_id);

      const audioBlob = base64ToBlob(result.answer_audio_base64, "audio/mpeg");
      const audio = new Audio(URL.createObjectURL(audioBlob));
      setCurrentAudio(audio);
      setSpeaking(true);
      audio.onended = () => setSpeaking(false);
      await audio.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice chat failed. Please try again.");
    } finally {
      setTranscribing(false);
    }
  };

  const handleClick = () => {
    if (isRecording) {
      void stopRecordingAndSend();
    } else {
      void startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={handleClick}
        disabled={isTranscribing}
        aria-label={isRecording ? "Stop recording" : "Start recording"}
        className={cn(
          "flex h-14 w-14 items-center justify-center rounded-full transition-colors",
          isRecording ? "animate-pulse bg-destructive text-destructive-foreground" : "bg-primary text-primary-foreground",
          isTranscribing && "opacity-60"
        )}
      >
        {isRecording ? <Square className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
      </button>
      {isTranscribing && <span className="text-xs text-muted-foreground">Thinking…</span>}
      {error && <span className="max-w-[220px] text-center text-xs text-destructive">{error}</span>}
    </div>
  );
}
