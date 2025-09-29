import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import api from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Initialize authentication state
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');
      const storedRefreshToken = localStorage.getItem('refreshToken');
      
      if (storedToken) {
        try {
          // Set token in API headers
          api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
          
          // Verify token and get user info
          const response = await api.get('/auth/me');
          setUser(response.data);
          setToken(storedToken);
        } catch (error) {
          console.error('Token verification failed:', error);
          
          // Try to refresh token
          if (storedRefreshToken) {
            try {
              const refreshResponse = await api.post('/auth/refresh', {
                refresh_token: storedRefreshToken
              });
              
              const newToken = refreshResponse.data.access_token;
              const newRefreshToken = refreshResponse.data.refresh_token;
              
              localStorage.setItem('token', newToken);
              localStorage.setItem('refreshToken', newRefreshToken);
              
              api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
              
              // Get user info with new token
              const userResponse = await api.get('/auth/me');
              setUser(userResponse.data);
              setToken(newToken);
            } catch (refreshError) {
              console.error('Token refresh failed:', refreshError);
              logout();
            }
          } else {
            logout();
          }
        }
      }
      
      setLoading(false);
    };

    initAuth();
  }, []);

  // Login function
  const login = async (credentials) => {
    try {
      setLoading(true);
      
      const response = await api.post('/auth/login', credentials);
      const { access_token, refresh_token, user: userData } = response.data;

      // Store tokens
      localStorage.setItem('token', access_token);
      localStorage.setItem('refreshToken', refresh_token);

      // Set authorization header
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Update state
      setToken(access_token);
      setUser(userData);

      message.success('Login berhasil!');
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const errorMessage = error.response?.data?.detail || 'Login gagal. Silakan coba lagi.';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      setLoading(true);
      
      const response = await api.post('/auth/register', userData);
      message.success('Registrasi berhasil! Silakan login.');
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Registration error:', error);
      const errorMessage = error.response?.data?.detail || 'Registrasi gagal. Silakan coba lagi.';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    // Clear tokens
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    
    // Clear authorization header
    delete api.defaults.headers.common['Authorization'];
    
    // Clear state
    setToken(null);
    setUser(null);
    
    message.info('Anda telah logout.');
  };

  // Change password function
  const changePassword = async (passwordData) => {
    try {
      await api.post('/auth/change-password', passwordData);
      message.success('Password berhasil diubah!');
      return { success: true };
    } catch (error) {
      console.error('Change password error:', error);
      const errorMessage = error.response?.data?.detail || 'Gagal mengubah password.';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // Update user profile
  const updateProfile = async (profileData) => {
    try {
      const response = await api.put('/auth/profile', profileData);
      setUser(response.data);
      message.success('Profile berhasil diperbarui!');
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Update profile error:', error);
      const errorMessage = error.response?.data?.detail || 'Gagal memperbarui profile.';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // Check if user has required role
  const hasRole = (requiredRole) => {
    if (!user) return false;
    if (!requiredRole) return true;
    
    const userRole = user.role?.toLowerCase();
    const required = requiredRole.toLowerCase();
    
    // Admin has access to everything
    if (userRole === 'admin') return true;
    
    // Check specific role
    return userRole === required;
  };

  // Check if user has permission
  const hasPermission = (permission) => {
    if (!user) return false;
    
    // Admin has all permissions
    if (user.role?.toLowerCase() === 'admin') return true;
    
    // Check user permissions
    return user.permissions?.includes(permission) || false;
  };

  // Refresh token function
  const refreshToken = async () => {
    try {
      const storedRefreshToken = localStorage.getItem('refreshToken');
      if (!storedRefreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await api.post('/auth/refresh', {
        refresh_token: storedRefreshToken
      });

      const newToken = response.data.access_token;
      const newRefreshToken = response.data.refresh_token;

      localStorage.setItem('token', newToken);
      localStorage.setItem('refreshToken', newRefreshToken);

      api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      setToken(newToken);

      return newToken;
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      throw error;
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    changePassword,
    updateProfile,
    hasRole,
    hasPermission,
    refreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};