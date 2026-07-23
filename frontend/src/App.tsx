import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from '@/components/layout/Header';
import ComponentsPage from '@/pages/ComponentsPage';
import ComponentDetailPage from '@/pages/ComponentDetailPage';
import UploadPage from '@/pages/UploadPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import HomePage from "@/pages/HomePage.tsx";
import AboutPage from "@/pages/AboutPage.tsx";
import WorkflowBuilderPage from "@/pages/WorkflowBuilderPage.tsx";
import ProfilePage from "@/pages/ProfilePage.tsx";
import ProtectedRoute from "@/pages/ProtectedRoutes.tsx";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Header />
        <main className="container mx-auto mt-14 max-w-6xl px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/browse" element={<ComponentsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/builder" element={<WorkflowBuilderPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/components/:id" element={<ComponentDetailPage />} />
            <Route path="/upload" element={<ProtectedRoute> <UploadPage /> </ProtectedRoute>} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Routes>
        </main>
      </Router>
    </QueryClientProvider>
  );
}
