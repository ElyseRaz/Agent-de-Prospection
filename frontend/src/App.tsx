import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import ProtectedRoute from "./components/layout/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import JobsSearchPage from "./pages/JobsSearchPage";
import JobDetailPage from "./pages/JobDetailPage";
import PipelinePage from "./pages/PipelinePage";
import ProfilePage from "./pages/ProfilePage";

function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedLayout>
            <DashboardPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/jobs"
        element={
          <ProtectedLayout>
            <JobsSearchPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/jobs/:jobId"
        element={
          <ProtectedLayout>
            <JobDetailPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/pipeline"
        element={
          <ProtectedLayout>
            <PipelinePage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedLayout>
            <ProfilePage />
          </ProtectedLayout>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
