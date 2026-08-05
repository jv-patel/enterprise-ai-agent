"use client";

import { useUser } from "@/contexts/UserContext";
import { OnboardingForm } from "@/components/onboarding/OnboardingForm";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  const { userId, isLoading } = useUser();

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</main>
    );
  }

  if (!userId) {
    return <OnboardingForm />;
  }

  return <ChatWindow />;
}
