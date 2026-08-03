import { create } from "zustand";

interface VoiceState {
  isRecording: boolean;
  isTranscribing: boolean;
  isSpeaking: boolean;
  transcript: string;
  currentAudio: HTMLAudioElement | null;
  setRecording: (value: boolean) => void;
  setTranscribing: (value: boolean) => void;
  setSpeaking: (value: boolean) => void;
  setTranscript: (transcript: string) => void;
  setCurrentAudio: (audio: HTMLAudioElement | null) => void;
  stopSpeaking: () => void;
}

export const useVoiceStore = create<VoiceState>((set, get) => ({
  isRecording: false,
  isTranscribing: false,
  isSpeaking: false,
  transcript: "",
  currentAudio: null,
  setRecording: (value) => set({ isRecording: value }),
  setTranscribing: (value) => set({ isTranscribing: value }),
  setSpeaking: (value) => set({ isSpeaking: value }),
  setTranscript: (transcript) => set({ transcript }),
  setCurrentAudio: (audio) => set({ currentAudio: audio }),
  stopSpeaking: () => {
    const audio = get().currentAudio;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    set({ isSpeaking: false, currentAudio: null });
  },
}));
