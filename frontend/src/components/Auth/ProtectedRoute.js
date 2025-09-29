import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Result, Button } from 'antd';
import { useAuth } from '../../contexts/AuthContext';

const ProtectedRoute = ({ children, requiredRole, requiredPermission }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Show loading while checking authentication
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">
          <div className="loading-text">Checking authentication...</div>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (requiredRole) {
    const userRole = user.role?.toLowerCase();
    const required = requiredRole.toLowerCase();
    
    // Admin has access to everything
    const hasAccess = userRole === 'admin' || userRole === required;
    
    if (!hasAccess) {
      return (
        <Result
          status="403"
          title="403"
          subTitle="Maaf, Anda tidak memiliki izin untuk mengakses halaman ini."
          extra={
            <Button type="primary" onClick={() => window.history.back()}>
              Kembali
            </Button>
          }
        />
      );
    }
  }

  // Check permission-based access
  if (requiredPermission) {
    const userRole = user.role?.toLowerCase();
    const hasPermission = userRole === 'admin' || 
                         user.permissions?.includes(requiredPermission);
    
    if (!hasPermission) {
      return (
        <Result
          status="403"
          title="403"
          subTitle="Maaf, Anda tidak memiliki izin untuk mengakses fitur ini."
          extra={
            <Button type="primary" onClick={() => window.history.back()}>
              Kembali
            </Button>
          }
        />
      );
    }
  }

  // Render protected content
  return children;
};

export default ProtectedRoute;