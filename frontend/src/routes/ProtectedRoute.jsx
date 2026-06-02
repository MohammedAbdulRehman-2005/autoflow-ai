import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#030712] flex flex-col items-center justify-center text-white space-y-4">
        {/* Animated glowing loader */}
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-4 border-cyan-500/10 animate-pulse"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-cyan-400 animate-spin"></div>
        </div>
        <p className="text-sm font-mono text-slate-400 tracking-wider">SECURE LINK INITIALIZING...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page, saving the location the user tried to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
