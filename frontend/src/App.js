import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout, Spin } from 'antd';
import { useAuth } from './contexts/AuthContext';
import { useTheme } from './contexts/ThemeContext';

// Layout components
import AppHeader from './components/Layout/AppHeader';
import AppSider from './components/Layout/AppSider';
import ProtectedRoute from './components/Auth/ProtectedRoute';

// Lazy load pages for better performance
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Login = React.lazy(() => import('./pages/Auth/Login'));
const OLTList = React.lazy(() => import('./pages/OLT/OLTList'));
const OLTDetail = React.lazy(() => import('./pages/OLT/OLTDetail'));
const ONTList = React.lazy(() => import('./pages/ONT/ONTList'));
const ONTDetail = React.lazy(() => import('./pages/ONT/ONTDetail'));
const Monitoring = React.lazy(() => import('./pages/Monitoring/Monitoring'));
const Alarms = React.lazy(() => import('./pages/Monitoring/Alarms'));
const Configuration = React.lazy(() => import('./pages/Configuration/Configuration'));
const BackupRestore = React.lazy(() => import('./pages/Configuration/BackupRestore'));
const ServiceProfiles = React.lazy(() => import('./pages/Configuration/ServiceProfiles'));
const Users = React.lazy(() => import('./pages/Users/Users'));
const Reports = React.lazy(() => import('./pages/Reports/Reports'));
const Settings = React.lazy(() => import('./pages/Settings/Settings'));
const Profile = React.lazy(() => import('./pages/Profile/Profile'));
const NotFound = React.lazy(() => import('./pages/NotFound'));

const { Content } = Layout;

// Loading component
const PageLoading = () => (
  <div className="loading-container">
    <div className="loading-spinner">
      <Spin size="large" />
      <div className="loading-text">Loading...</div>
    </div>
  </div>
);

function App() {
  const { user, loading: authLoading } = useAuth();
  const { theme } = useTheme();

  // Show loading spinner while checking authentication
  if (authLoading) {
    return <PageLoading />;
  }

  // If user is not authenticated, show login page
  if (!user) {
    return (
      <div className="app" data-theme={theme}>
        <Suspense fallback={<PageLoading />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Suspense>
      </div>
    );
  }

  // Main application layout for authenticated users
  return (
    <div className="app" data-theme={theme}>
      <Layout className="app-layout">
        <AppSider />
        <Layout>
          <AppHeader />
          <Content className="app-content">
            <Suspense fallback={<PageLoading />}>
              <Routes>
                {/* Dashboard */}
                <Route 
                  path="/" 
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/dashboard" 
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  } 
                />

                {/* OLT Management */}
                <Route 
                  path="/olts" 
                  element={
                    <ProtectedRoute>
                      <OLTList />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/olts/:id" 
                  element={
                    <ProtectedRoute>
                      <OLTDetail />
                    </ProtectedRoute>
                  } 
                />

                {/* ONT Management */}
                <Route 
                  path="/onts" 
                  element={
                    <ProtectedRoute>
                      <ONTList />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/onts/:id" 
                  element={
                    <ProtectedRoute>
                      <ONTDetail />
                    </ProtectedRoute>
                  } 
                />

                {/* Monitoring */}
                <Route 
                  path="/monitoring" 
                  element={
                    <ProtectedRoute>
                      <Monitoring />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/alarms" 
                  element={
                    <ProtectedRoute>
                      <Alarms />
                    </ProtectedRoute>
                  } 
                />

                {/* Configuration */}
                <Route 
                  path="/configuration" 
                  element={
                    <ProtectedRoute requiredRole="admin">
                      <Configuration />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/backup-restore" 
                  element={
                    <ProtectedRoute requiredRole="admin">
                      <BackupRestore />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/service-profiles" 
                  element={
                    <ProtectedRoute>
                      <ServiceProfiles />
                    </ProtectedRoute>
                  } 
                />

                {/* User Management */}
                <Route 
                  path="/users" 
                  element={
                    <ProtectedRoute requiredRole="admin">
                      <Users />
                    </ProtectedRoute>
                  } 
                />

                {/* Reports */}
                <Route 
                  path="/reports" 
                  element={
                    <ProtectedRoute>
                      <Reports />
                    </ProtectedRoute>
                  } 
                />

                {/* Settings */}
                <Route 
                  path="/settings" 
                  element={
                    <ProtectedRoute requiredRole="admin">
                      <Settings />
                    </ProtectedRoute>
                  } 
                />

                {/* Profile */}
                <Route 
                  path="/profile" 
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  } 
                />

                {/* Auth routes */}
                <Route path="/login" element={<Navigate to="/dashboard" replace />} />

                {/* 404 */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </Content>
        </Layout>
      </Layout>
    </div>
  );
}

export default App;