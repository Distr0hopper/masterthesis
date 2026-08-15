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
import MyWorkflowsPage from '@/pages/MyWorkflowsPage';
import LoginPage from '@/pages/LoginPage';
import HomePage from "@/pages/HomePage.tsx";
import AboutPage from "@/pages/AboutPage.tsx";
import WorkflowBuilderPage from "@/pages/WorkflowBuilderPage.tsx";
import ProfilePage from "@/pages/ProfilePage.tsx";
import ProtectedRoute from "@/pages/ProtectedRoutes.tsx";
import { Toaster } from "@/components/ui/sonner.tsx";
import { ROUTES } from "@/lib/routes";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Toaster />
        <Header />
        <main className="container mx-auto mt-14 max-w-6xl px-4 py-8">
          <Routes>
            <Route path={ROUTES.home} element={<HomePage />} />
            <Route path={ROUTES.browse} element={<ComponentsPage />} />
            <Route path={ROUTES.about} element={<AboutPage />} />
            <Route path={ROUTES.builder} element={<WorkflowBuilderPage />} />
            <Route path={ROUTES.profile} element={<ProtectedRoute> <ProfilePage /> </ProtectedRoute>} />
            <Route path={ROUTES.componentDetail(':id')} element={<ComponentDetailPage />} />
            <Route path={ROUTES.componentUpload} element={<ProtectedRoute> <UploadPage /> </ProtectedRoute>} />
            <Route path={ROUTES.myComponents} element={<ProtectedRoute> <MyComponentsPage /> </ProtectedRoute>} />
            <Route path={ROUTES.workflows} element={<WorkflowsPage />} />
            <Route path={ROUTES.workflowUpload} element={<ProtectedRoute> <WorkflowUploadPage /> </ProtectedRoute>} />
            <Route path={ROUTES.workflowDetail(':id')} element={<WorkflowDetailPage />} />
            <Route path={ROUTES.myWorkflows} element={<ProtectedRoute> <MyWorkflowsPage /> </ProtectedRoute>} />
            <Route path={ROUTES.login} element={<LoginPage />} />
          </Routes>
        </main>
      </Router>
    </QueryClientProvider>
  );
}
