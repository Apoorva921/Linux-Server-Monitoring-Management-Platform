import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { LoadingSpinner } from './components/Feedback';
import { AuthProvider, useAuth } from './hooks/AuthContext';
import { WebSocketProvider } from './hooks/useMetricsWebSocket';
import { DashboardLayout } from './layouts/DashboardLayout';
import { AlertsPage } from './pages/AlertsPage';
import { LoginPage } from './pages/LoginPage';
import { LogsPage } from './pages/LogsPage';
import { MonitoringPage } from './pages/MonitoringPage';
import { OverviewPage } from './pages/OverviewPage';
import { ProcessesPage } from './pages/ProcessesPage';
import { ServerDetailPage } from './pages/ServerDetailPage';
import { ServersPage } from './pages/ServersPage';
import { SettingsPage } from './pages/SettingsPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F8FC] flex items-center justify-center">
        <LoadingSpinner label="Verifying session..." />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

export const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/"
      element={
        <ProtectedRoute>
          <DashboardLayout />
        </ProtectedRoute>
      }
    >
      <Route index element={<OverviewPage />} />
      <Route path="servers" element={<ServersPage />} />
      <Route path="servers/:serverId" element={<ServerDetailPage />} />
      <Route path="monitoring" element={<MonitoringPage />} />
      <Route path="alerts" element={<AlertsPage />} />
      <Route path="logs" element={<LogsPage />} />
      <Route path="processes" element={<ProcessesPage />} />
      <Route path="settings" element={<SettingsPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export const App: React.FC = () => (
  <BrowserRouter>
    <AuthProvider>
      <WebSocketProvider>
        <AppRoutes />
      </WebSocketProvider>
    </AuthProvider>
  </BrowserRouter>
);

export default App;
