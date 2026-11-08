import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { clearAccessToken } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [college, setCollege] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const initAuth = useCallback(async () => {
    try {
      // Attempt silent refresh using HttpOnly cookie
      await authApi.refresh();
      // Fetch authenticated user profile and college information
      const meResponse = await authApi.getMe();
      if (meResponse?.data) {
        setUser(meResponse.data.user);
        setCollege(meResponse.data.college);
        setIsAuthenticated(true);
      }
    } catch {
      // Session does not exist or expired; remain unauthenticated
      clearAccessToken();
      setUser(null);
      setCollege(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initAuth();

    const handleAuthExpired = () => {
      setUser(null);
      setCollege(null);
      setIsAuthenticated(false);
    };

    window.addEventListener('campuscycle:auth_expired', handleAuthExpired);
    return () => {
      window.removeEventListener('campuscycle:auth_expired', handleAuthExpired);
    };
  }, [initAuth]);

  const login = async (credentials) => {
    setError(null);
    try {
      await authApi.login(credentials);
      const meResponse = await authApi.getMe();
      if (meResponse?.data) {
        setUser(meResponse.data.user);
        setCollege(meResponse.data.college);
        setIsAuthenticated(true);
        return { success: true, data: meResponse.data };
      }
      return { success: true };
    } catch (err) {
      const message =
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        'Login failed. Please check your credentials.';
      setError(message);
      throw new Error(message);
    }
  };

  const register = async (registrationData) => {
    setError(null);
    try {
      const res = await authApi.register(registrationData);
      return res;
    } catch (err) {
      const message =
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        'Registration failed. Please check your details.';
      setError(message);
      throw new Error(message);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Even if network or cookie fails, clear client state
    } finally {
      clearAccessToken();
      setUser(null);
      setCollege(null);
      setIsAuthenticated(false);
    }
  };

  const clearError = () => setError(null);

  const value = {
    user,
    college,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
    refreshUser: initAuth,
    isPlatformAdmin: user?.role === 'platform_admin',
    isCollegeRep: user?.role === 'college_representative',
    isVerifiedCollege: college?.verification_status === 'verified',
    isPendingCollege: college?.verification_status === 'pending',
    isRejectedCollege: college?.verification_status === 'rejected',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
