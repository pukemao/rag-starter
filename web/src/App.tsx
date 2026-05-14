import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { ChatPage } from "@/pages/ChatPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DeletePage } from "@/pages/DeletePage";
import { IndexPage } from "@/pages/IndexPage";
import { KnowledgeBasePage } from "@/pages/KnowledgeBasePage";
import { RagChatPage } from "@/pages/RagChatPage";
import { SearchPage } from "@/pages/SearchPage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/knowledge" replace />} />
        <Route path="/knowledge" element={<KnowledgeBasePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/status" element={<DashboardPage />} />
        <Route path="/index" element={<IndexPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/rag-chat" element={<RagChatPage />} />
        <Route path="/delete" element={<DeletePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
