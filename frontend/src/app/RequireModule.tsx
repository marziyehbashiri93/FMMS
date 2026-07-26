import { useEffect, useState, type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { api } from '../api/client';
import type { AuthUser } from '../types/fmms';
import { canAccessModule } from './access';

type RequireModuleProps = {
  moduleKey: string;
  children: ReactNode;
};

/**
 * Block direct URL access when the authenticated role cannot open the module.
 */
export function RequireModule({ moduleKey, children }: RequireModuleProps) {
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    void api
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (user === undefined) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 240 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (!canAccessModule(user, moduleKey)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
