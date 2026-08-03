const DEFAULT_WS_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/^http/, "ws");

export interface StreamingTranscriptResult {
  transcript: string;
  is_final: boolean;
}

export interface StreamingVoiceHandlers {
  onResult: (result: StreamingTranscriptResult) => void;
  onError?: (message: string) => void;
  onClose?: () => void;
}

/**
 * Streams microphone audio to the backend's real-time STT WebSocket and
 * surfaces interim/final transcript results as they arrive.
 */
export class StreamingVoiceClient {
  private socket: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;

  async start(handlers: StreamingVoiceHandlers): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.socket = new WebSocket(`${DEFAULT_WS_BASE_URL}/voice/stream`);
    this.socket.binaryType = "arraybuffer";

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.error) {
          handlers.onError?.(data.error);
          return;
        }
        handlers.onResult(data as StreamingTranscriptResult);
      } catch {
        handlers.onError?.("Received an unreadable message from the voice stream.");
      }
    };
    this.socket.onerror = () => handlers.onError?.("Voice stream connection error.");
    this.socket.onclose = () => handlers.onClose?.();

    await new Promise<void>((resolve, reject) => {
      if (!this.socket) return reject(new Error("Socket not initialized."));
      this.socket.onopen = () => resolve();
    });

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0 && this.socket?.readyState === WebSocket.OPEN) {
        event.data.arrayBuffer().then((buffer) => this.socket?.send(buffer));
      }
    };
    // Emit a chunk every 250ms for low-latency streaming recognition.
    this.mediaRecorder.start(250);
  }

  stop(): void {
    this.mediaRecorder?.stop();
    this.stream?.getTracks().forEach((track) => track.stop());
    this.socket?.close();
    this.mediaRecorder = null;
    this.stream = null;
    this.socket = null;
  }
}
