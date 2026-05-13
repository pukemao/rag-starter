import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { DeletePage } from "@/pages/DeletePage";
import { IndexPage } from "@/pages/IndexPage";
import { RagChatPage } from "@/pages/RagChatPage";
import { SearchPage } from "@/pages/SearchPage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/index" element={<IndexPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/chat" element={<RagChatPage />} />
        <Route path="/delete" element={<DeletePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
