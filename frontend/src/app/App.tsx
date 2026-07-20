import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, Card, CardContent, Typography } from '@mui/material';
import { AppLayout } from '../layouts/AppLayout';
import { api } from '../api/client';
import { LoginPage } from '../features/auth/LoginPage';
import { VehiclePage } from '../features/vehicles/VehiclePage';
import { ComponentShowcasePage } from '../features/showcase/ComponentShowcasePage';
import { modules } from './modules';

function PlaceholderPage({ label }: { label: string }) {
  return (
    <Box maxWidth={720}>
      <Card>
        <CardContent>
          <Typography variant="h2" mb={1}>{label}</Typography>
          <Typography color="text.secondary">
            این بخش در فازهای بعدی صفحه‌به‌صفحه فعال می‌شود.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}

function RequireAuth() {
  if (!api.getAccessToken()) return <Navigate to="/login" replace />;
  return <AppLayout />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<Navigate to="/vehicles" replace />} />
        <Route path="/vehicles" element={<VehiclePage />} />
        <Route path="/components" element={<ComponentShowcasePage />} />
        {modules.filter((item) => !item.enabled).map((item) => (
          <Route key={item.key} path={item.path} element={<PlaceholderPage label={item.label} />} />
        ))}
      </Route>
      <Route path="*" element={<Navigate to="/vehicles" replace />} />
    </Routes>
  );
}
