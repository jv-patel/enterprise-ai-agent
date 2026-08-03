"use client";

import { useRef, useState } from "react";
import { Loader2, Upload } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface UploadedFile {
  id: string;
  file_name: string;
  file_type: string;
  created_at: string;
  summary: string | null;
}

interface FileUploadWidgetProps {
  userId: string;
  chatId?: string;
  onUploaded?: (file: UploadedFile) => void;
}

export function FileUploadWidget({ userId, chatId, onUploaded }: FileUploadWidgetProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (chatId) formData.append("chat_id", chatId);

      const uploaded = await apiFetch<UploadedFile>("/files/upload", {
        method: "POST",
        body: formData,
        userId,
      });
      onUploaded?.(uploaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        void handleFiles(event.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed",
        "border-border p-6 text-center transition-colors hover:border-primary/50"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.gif"
        className="hidden"
        onChange={(event) => void handleFiles(event.target.files)}
      />
      {isUploading ? (
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      ) : (
        <Upload className="h-8 w-8 text-muted-foreground" />
      )}
      <p className="text-sm text-muted-foreground">{isUploading ? "Uploading…" : "Drop a file here or click to upload"}</p>
      <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, CSV, Excel, or images</p>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
