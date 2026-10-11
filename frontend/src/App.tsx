import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Navigate, Routes, Route } from 'react-router-dom';
import Header from '@/components/layout/Header';
import { ContainerLayout } from '@/components/layout/ContainerLayout';
import { FullBleedLayout } from '@/components/layout/FullBleedLayout';
import ComponentsPage from '@/pages/ComponentsPage';
import ComponentDetailPage from '@/pages/ComponentDetailPage';
import ToolUploadPage from '@/pages/ToolUploadPage';
import MyComponentsPage from '@/pages/MyComponentsPage';
import WorkflowUploadPage from '@/pages/WorkflowUploadPage';
import LoginPage from '@/pages/LoginPage';
import HomePage from "@/pages/HomePage.tsx";
import AboutPage from "@/pages/AboutPage.tsx";
import WorkflowBuilderPage from "@/pages/WorkflowBuilderPage.tsx";
import WorkflowBuilderOverviewPage from "@/pages/WorkflowBuilderOverviewPage.tsx";
import ProfilePage from "@/pages/ProfilePage.tsx";
import ProtectedRoute from "@/pages/ProtectedRoutes.tsx";
import { Toaster } from "@/components/ui/sonner.tsx";
import { SessionKeeper } from "@/api/auth/SessionKeeper";
import { ROUTES, browseRoute } from "@/lib/routes";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Toaster />
        <SessionKeeper />
        <Header />
        <Routes>
          {/* Layout routes rather than one hardcoded <main>: the builder needs the full
              viewport, every other page keeps the centred max-w-6xl container. */}
          <Route element={<ContainerLayout />}>
            <Route path={ROUTES.home} element={<HomePage />} />
            <Route path={ROUTES.about} element={<AboutPage />} />
            <Route path={ROUTES.profile} element={<ProtectedRoute> <ProfilePage /> </ProtectedRoute>} />

            {/* one browse list for both kinds; the other pages are parameterised by kind */}
            <Route path={ROUTES.browse} element={<ComponentsPage />} />
            <Route path={ROUTES.toolUpload} element={<ProtectedRoute> <ToolUploadPage /> </ProtectedRoute>} />
            <Route path={ROUTES.toolDetail(':id')} element={<ComponentDetailPage key="tool" kind="tool" />} />
            <Route path={ROUTES.myTools} element={<ProtectedRoute> <MyComponentsPage key="tool" kind="tool" /> </ProtectedRoute>} />
            <Route path={ROUTES.workflowUpload} element={<ProtectedRoute> <WorkflowUploadPage /> </ProtectedRoute>} />
            <Route path={ROUTES.workflowDetail(':id')} element={<ComponentDetailPage key="workflow" kind="workflow" />} />
            <Route path={ROUTES.myWorkflows} element={<ProtectedRoute> <MyComponentsPage key="workflow" kind="workflow" /> </ProtectedRoute>} />

            {/* old paths - the per-kind lists and the pre-split component pages - existing links keep working */}
            <Route path={ROUTES.legacyTools} element={<Navigate to={browseRoute({ kind: 'tool' })} replace />} />
            <Route path={ROUTES.legacyWorkflows} element={<Navigate to={browseRoute({ kind: 'workflow' })} replace />} />
            <Route path={ROUTES.legacyComponents} element={<Navigate to={ROUTES.browse} replace />} />
            <Route path={ROUTES.legacyMyComponents} element={<Navigate to={ROUTES.myTools} replace />} />
            <Route path={ROUTES.legacyComponentUpload} element={<Navigate to={ROUTES.toolUpload} replace />} />
            {/* resolves the kind, then redirects to /tools/:id or /workflows/:id */}
            <Route path={ROUTES.componentDetail(':id')} element={<ComponentDetailPage />} />
            <Route path={ROUTES.login} element={<LoginPage />} />
            <Route path={ROUTES.builder} element={<WorkflowBuilderOverviewPage />} />
          </Route>

          <Route element={<FullBleedLayout />}>
            {/* the literal route must precede the dynamic one */}
            <Route path={ROUTES.builderNew} element={<WorkflowBuilderPage />} />
            <Route path={ROUTES.builderWorkflow(':id')} element={<WorkflowBuilderPage />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}
