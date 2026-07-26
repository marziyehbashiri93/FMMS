import { useEffect, useState } from 'react';
import { Box, Card, CardActionArea, CardContent, Stack, Typography } from '@mui/material';
import {
  Build,
  CarRepair,
  DirectionsCar,
  ErrorOutline,
  PeopleAlt,
  Speed,
  Sync,
  TaskAlt,
} from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../../api/client';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { ErrorState, LoadingState } from '../../components/States';
import type { DriverSummary, SAPTransactionSummary, VehicleSummary } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

type QueueCounts = {
  openFaults: number;
  transportQueue: number;
  workshopQueue: number;
};

type QuickLink = {
  title: string;
  subtitle: string;
  to: string;
  icon: typeof DirectionsCar;
  tone: 'primary' | 'warning' | 'success' | 'error';
};

/**
 * Operations dashboard built from vehicle/driver summary APIs and queue counts.
 */
export function DashboardPage() {
  const [vehicleSummary, setVehicleSummary] = useState<VehicleSummary | null>(null);
  const [driverSummary, setDriverSummary] = useState<DriverSummary | null>(null);
  const [sapSummary, setSapSummary] = useState<SAPTransactionSummary | null>(null);
  const [queues, setQueues] = useState<QueueCounts>({
    openFaults: 0,
    transportQueue: 0,
    workshopQueue: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [
        vehicles,
        drivers,
        openFaults,
        transportCreated,
        transportApproved,
        workshopQueue,
        sap,
      ] = await Promise.all([
          api.getVehicleSummary(),
          api.getDriverSummary(),
          api.listFaults(undefined, { status: 'OPEN', page: 1, pageSize: 1 }),
          api.listRepairOrders({ status: 'CREATED', page: 1, pageSize: 1 }),
          api.listRepairOrders({ status: 'APPROVED', page: 1, pageSize: 1 }),
          api.listRepairOrders({
            status: 'WORKSHOP_ASSIGNED',
            workshopType: 'INTERNAL',
            page: 1,
            pageSize: 1,
          }),
          api.getSapTransactionSummary().catch(() => null),
        ]);
      setVehicleSummary(vehicles);
      setDriverSummary(drivers);
      setSapSummary(sap);
      setQueues({
        openFaults: openFaults.count ?? 0,
        transportQueue: (transportCreated.count ?? 0) + (transportApproved.count ?? 0),
        workshopQueue: workshopQueue.count ?? 0,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خلاصه داشبورد بارگذاری نشد');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const quickLinks: QuickLink[] = [
    {
      title: 'کارتابل توزیع',
      subtitle: `${toFaNumber(queues.openFaults)} خرابی در انتظار تصمیم توزیع`,
      to: '/faults',
      icon: CarRepair,
      tone: 'warning',
    },
    {
      title: 'کارتابل ترابری',
      subtitle: `${toFaNumber(queues.transportQueue)} درخواست در صف ترابری`,
      to: '/repairs',
      icon: Build,
      tone: 'error',
    },
    {
      title: 'تعمیرگاه مرکزی',
      subtitle: `${toFaNumber(queues.workshopQueue)} درخواست در انتظار تصمیم فنی`,
      to: '/workshop',
      icon: Build,
      tone: 'warning',
    },
    {
      title: 'خودروها',
      subtitle: `${toFaNumber(vehicleSummary?.active_fleet_count)} خودرو فعال`,
      to: '/vehicles',
      icon: DirectionsCar,
      tone: 'primary',
    },
    {
      title: 'راننده‌ها',
      subtitle: `${toFaNumber(driverSummary?.active_count)} راننده فعال`,
      to: '/drivers',
      icon: PeopleAlt,
      tone: 'success',
    },
    {
      title: 'وضعیت SAP',
      subtitle: sapSummary
        ? `${toFaNumber(sapSummary.failed + sapSummary.exhausted)} ناموفق · ${toFaNumber(sapSummary.success)} موفق`
        : 'مشاهده وضعیت همگام‌سازی و تراکنش‌ها',
      to: '/sap',
      icon: Sync,
      tone: 'primary',
    },
  ];

  return (
    <FeaturePage>
      <PageHeader
        title="نمای کلی عملیات ناوگان"
        description="خلاصه وضعیت ناوگان، راننده‌ها و صف‌های عملیاتی بر اساس آخرین داده‌ها."
        breadcrumbs={[{ label: 'داشبورد' }]}
      />

      {error && <ErrorState message={error} onRetry={() => void load()} />}
      {loading && !error && <LoadingState label="در حال بارگذاری داشبورد…" />}

      {!loading && !error && (
        <>
          <KpiGrid mdColumns={4}>
            <KpiCard
              label="خودروهای فعال"
              value={toFaNumber(vehicleSummary?.active_fleet_count)}
              icon={DirectionsCar}
              tone="primary"
            />
            <KpiCard
              label="آماده بهره‌برداری"
              value={toFaNumber(vehicleSummary?.operational_fleet_count)}
              icon={TaskAlt}
              tone="success"
            />
            <KpiCard
              label="خودروهای در تعمیر"
              value={toFaNumber(vehicleSummary?.under_repair_fleet_count)}
              icon={Build}
              tone="warning"
            />
            <KpiCard
              label="خودروهای خارج از سرویس"
              value={toFaNumber(vehicleSummary?.unusable_fleet_count)}
              icon={ErrorOutline}
              tone="error"
            />
          </KpiGrid>

          <KpiGrid mdColumns={4}>
            <KpiCard
              label="راننده‌های فعال"
              value={toFaNumber(driverSummary?.active_count)}
              icon={PeopleAlt}
              tone="primary"
            />
            <KpiCard
              label="راننده‌های دارای خودرو"
              value={toFaNumber(driverSummary?.with_vehicle_count)}
              icon={DirectionsCar}
              tone="info"
            />
            <KpiCard
              label="میانگین کارکرد خودروها"
              value={toFaNumber(vehicleSummary?.average_odometer_km)}
              icon={Speed}
              tone="info"
            />
            <KpiCard
              label="میانگین خرابی در ۳۰ روز اخیر"
              value={toFaNumber(vehicleSummary?.average_faults_last_30_days)}
              icon={CarRepair}
              tone="warning"
            />
          </KpiGrid>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                md: 'repeat(2, minmax(0, 1fr))',
                lg: 'repeat(4, minmax(0, 1fr))',
              },
              gap: 1.5,
            }}
          >
            {quickLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Card key={link.to} variant="outlined">
                  <CardActionArea
                    component={RouterLink}
                    to={link.to}
                    sx={{ height: '100%', alignItems: 'stretch' }}
                  >
                    <CardContent
                      sx={{
                        p: 1.75,
                        '&:last-child': { pb: 1.75 },
                        display: 'flex',
                        gap: 1.5,
                        alignItems: 'center',
                        direction: 'rtl',
                      }}
                    >
                      <Box
                        sx={{
                          width: 44,
                          height: 44,
                          borderRadius: (t) => t.radius('lg'),
                          bgcolor: `${link.tone}.light`,
                          color: `${link.tone}.dark`,
                          display: 'grid',
                          placeItems: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <Icon fontSize="medium" />
                      </Box>
                      <Box minWidth={0} textAlign="right">
                        <Typography fontWeight={800}>{link.title}</Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>
                          {link.subtitle}
                        </Typography>
                      </Box>
                    </CardContent>
                  </CardActionArea>
                </Card>
              );
            })}
          </Box>

          <Card variant="outlined">
            <CardActionArea component={RouterLink} to="/sap">
              <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                <Stack direction="row" spacing={1.25} alignItems="center">
                  <Sync color="action" />
                  <Box>
                    <Typography fontWeight={800}>همگام‌سازی و تراکنش‌های SAP</Typography>
                    <Typography variant="body2" color="text.secondary">
                      خودرو: {formatDateTime(vehicleSummary?.last_sap_sync_at)} · راننده:{' '}
                      {formatDateTime(driverSummary?.last_sap_sync_at)}
                      {sapSummary
                        ? ` · کل تراکنش‌ها: ${toFaNumber(sapSummary.total)} · ناموفق: ${toFaNumber(sapSummary.failed + sapSummary.exhausted)}`
                        : ''}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </CardActionArea>
          </Card>
        </>
      )}
    </FeaturePage>
  );
}
