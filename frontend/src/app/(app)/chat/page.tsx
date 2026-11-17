import type { Metadata } from "next";
import { ChatIndex } from "@/components/chat/chat-shell";

export const metadata: Metadata = { title: "Conversas" };

export default function ChatPage() {
  return <ChatIndex />;
}
