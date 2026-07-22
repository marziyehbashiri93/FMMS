import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, Card, CardContent, Typography } from '@mui/material';
import { AppLayout } from '../layouts/AppLayout';
import { api } from '../api/client';
import { LoginPage } from '../features/auth/LoginPage';
import { VehiclePage } from '../features/vehicles/VehiclePage';
import { DriversPage } from '../features/drivers/DriversPage';
import { ChecklistsPage } from '../features/inspections/ChecklistsPage';
import { InspectionPage } from '../features/inspections/InspectionPage';
import { ManualFaultPage } from '../features/faults/ManualFaultPage';
import { ComponentShowcasePage } from '../features/showcase/ComponentShowcasePage';
import { modules } from './modules';

function PlaceholderPage({ label }: { label: string }) {
  return (
    <Box maxWidth={720}>
      <Card>
        <CardContent>
          <Typography variant="h2" mb={1}>
            {label}
          </Typography>
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

const dedicatedPaths = new Set([
  '/vehicles',
  '/checklists',
  '/drivers',
  '/inspections',
  '/faults',
  '/components',
]);

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<Navigate to="/vehicles" replace />} />
        <Route path="/vehicles" element={<VehiclePage />} />
        <Route path="/checklists" element={<ChecklistsPage />} />
        <Route path="/drivers" element={<DriversPage />} />
        <Route path="/drivers/:driverId" element={<DriversPage />} />
        <Route path="/inspections" element={<InspectionPage />} />
        <Route path="/faults" element={<ManualFaultPage />} />
        <Route path="/components" element={<ComponentShowcasePage />} />
        {modules
          .filter((item) => !item.enabled && !dedicatedPaths.has(item.path))
          .map((item) => (
            <Route key={item.key} path={item.path} element={<PlaceholderPage label={item.label} />} />
          ))}
      </Route>
      <Route path="*" element={<Navigate to="/vehicles" replace />} />
    </Routes>
  );
}
