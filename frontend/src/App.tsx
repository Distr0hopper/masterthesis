import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from '@/components/layout/Header';
import ComponentsPage from '@/pages/ComponentsPage';
import ComponentDetailPage from '@/pages/ComponentDetailPage';
import UploadPage from '@/pages/UploadPage';
import MyComponentsPage from '@/pages/MyComponentsPage';
import WorkflowsPage from '@/pages/WorkflowsPage';
import WorkflowDetailPage from '@/pages/WorkflowDetailPage';
import WorkflowUploadPage from '@/pages/WorkflowUploadPage';
import LoginPage from '@/pages/LoginPage';
import HomePage from "@/pages/HomePage.tsx";
import AboutPage from "@/pages/AboutPage.tsx";
import WorkflowBuilderPage from "@/pages/WorkflowBuilderPage.tsx";
import ProfilePage from "@/pages/ProfilePage.tsx";
import ProtectedRoute from "@/pages/ProtectedRoutes.tsx";
import { Toaster } from "@/components/ui/sonner.tsx";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Toaster />
        <Header />
        <main className="container mx-auto mt-14 max-w-6xl px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/browse" element={<ComponentsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/builder" element={<WorkflowBuilderPage />} />
            <Route path="/profile" element={<ProtectedRoute> <ProfilePage /> </ProtectedRoute>} />
            <Route path="/components/:id" element={<ComponentDetailPage />} />
            <Route path="/upload" element={<ProtectedRoute> <UploadPage /> </ProtectedRoute>} />
            <Route path="/my-components" element={<ProtectedRoute> <MyComponentsPage /> </ProtectedRoute>} />
            <Route path="/workflows" element={<WorkflowsPage />} />
            <Route path="/workflows/upload" element={<ProtectedRoute> <WorkflowUploadPage /> </ProtectedRoute>} />
            <Route path="/workflows/:id" element={<WorkflowDetailPage />} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </main>
      </Router>
    </QueryClientProvider>
  );
}
