import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from '@/components/layout/Header';
import ComponentsPage from '@/pages/ComponentsPage';
import ComponentDetailPage from '@/pages/ComponentDetailPage';
import UploadPage from '@/pages/UploadPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Header />
        <main className="container mx-auto max-w-6xl px-4 py-8">
          <Routes>
            <Route path="/" element={<ComponentsPage />} />
            <Route path="/components/:id" element={<ComponentDetailPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Routes>
        </main>
      </Router>
    </QueryClientProvider>
  );
}
