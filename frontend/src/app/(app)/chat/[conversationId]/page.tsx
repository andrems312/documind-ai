import type { Metadata } from "next";
import { ChatThread } from "@/components/chat/chat-thread";

export const metadata: Metadata = { title: "Conversa" };

export default function ConversationPage() {
  return <ChatThread />;
}
