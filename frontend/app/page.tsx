import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
        Enterprise AI Personal Agent
      </h1>
      <p className="max-w-xl text-muted-foreground">
        Your AI-powered assistant for chat, voice, vision, email, calendar,
        files, and automated multi-agent task execution.
      </p>
      <Link
        href="/chat"
        className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
      >
        Open Chat
      </Link>
    </main>
  );
}
