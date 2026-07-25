import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, Card, CardContent, Typography } from '@mui/material';
import { AppLayout } from '../layouts/AppLayout';
import { api } from '../api/client';
import { LoginPage } from '../features/auth/LoginPage';
import { VehiclePage } from '../features/vehicles/VehiclePage';
import { DriversPage } from '../features/drivers/DriversPage';
import { ChecklistsPage } from '../features/inspections/ChecklistsPage';
import { InspectionPage } from '../features/inspections/InspectionPage';
import { DistributionFaultsPage } from '../features/faults/DistributionFaultsPage';
import { ManualFaultPage } from '../features/faults/ManualFaultPage';
import { TransportRepairsPage } from '../features/repairs/TransportRepairsPage';
import { CentralWorkshopPage } from '../features/workshop/CentralWorkshopPage';
import { HandoverPage } from '../features/handover/HandoverPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { SapTransactionsPage } from '../features/sap/SapTransactionsPage';
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
  '/dashboard',
  '/vehicles',
  '/checklists',
  '/drivers',
  '/inspections',
  '/faults',
  '/faults/new',
  '/repairs',
  '/workshop',
  '/handover',
  '/sap',
  '/components',
]);

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/vehicles" element={<VehiclePage />} />
        <Route path="/checklists" element={<ChecklistsPage />} />
        <Route path="/drivers" element={<DriversPage />} />
        <Route path="/drivers/:driverId" element={<DriversPage />} />
        <Route path="/inspections" element={<InspectionPage />} />
        <Route path="/faults" element={<DistributionFaultsPage />} />
        <Route path="/faults/new" element={<ManualFaultPage />} />
        <Route path="/repairs" element={<TransportRepairsPage />} />
        <Route path="/workshop" element={<CentralWorkshopPage />} />
        <Route path="/handover" element={<HandoverPage />} />
        <Route path="/sap" element={<SapTransactionsPage />} />
        <Route path="/components" element={<ComponentShowcasePage />} />
        {modules
          .filter((item) => !item.enabled && !dedicatedPaths.has(item.path))
          .map((item) => (
            <Route key={item.key} path={item.path} element={<PlaceholderPage label={item.label} />} />
          ))}
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
