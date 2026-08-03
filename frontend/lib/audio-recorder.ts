export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private stream: MediaStream | null = null;

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.chunks = [];

    const preferredMimeType = "audio/webm;codecs=opus";
    const mimeType = MediaRecorder.isTypeSupported(preferredMimeType) ? preferredMimeType : "audio/webm";

    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.chunks.push(event.data);
      }
    };
    this.mediaRecorder.start();
  }

  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error("Recorder was never started."));
        return;
      }
      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: "audio/webm" });
        this.stream?.getTracks().forEach((track) => track.stop());
        resolve(blob);
      };
      this.mediaRecorder.stop();
    });
  }

  get isRecording(): boolean {
    return this.mediaRecorder?.state === "recording";
  }
}
