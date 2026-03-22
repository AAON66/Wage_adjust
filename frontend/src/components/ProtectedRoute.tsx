import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { getRoleHomePath } from '../utils/roleAccess';

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, isBootstrapping, user } = useAuth();
  const location = useLocation();

  if (isBootstrapping) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-sand px-6 text-ink">
        <div className="surface px-5 py-3 text-sm font-medium">正在校验登录状态...</div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }

  if (user?.must_change_password && location.pathname !== '/settings') {
    return <Navigate replace state={{ forcePasswordChange: true, from: location.pathname }} to="/settings" />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate replace to={getRoleHomePath(user.role)} />;
  }

  return <Outlet />;
}
