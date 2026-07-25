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
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { ErrorState, LoadingState } from '../../components/States';
import type { DriverSummary, SAPTransactionSummary, VehicleSummary } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

type QueueCounts = {
  openFaults: number;
  transportQueue: number;
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
  const [queues, setQueues] = useState<QueueCounts>({ openFaults: 0, transportQueue: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [vehicles, drivers, openFaults, transportCreated, transportApproved, sap] =
        await Promise.all([
          api.getVehicleSummary(),
          api.getDriverSummary(),
          api.listFaults(undefined, { status: 'OPEN', page: 1, pageSize: 1 }),
          api.listRepairOrders({ status: 'CREATED', page: 1, pageSize: 1 }),
          api.listRepairOrders({ status: 'APPROVED', page: 1, pageSize: 1 }),
          api.getSapTransactionSummary().catch(() => null),
        ]);
      setVehicleSummary(vehicles);
      setDriverSummary(drivers);
      setSapSummary(sap);
      setQueues({
        openFaults: openFaults.count ?? 0,
        transportQueue: (transportCreated.count ?? 0) + (transportApproved.count ?? 0),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت خلاصه داشبورد انجام نشد');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const quickLinks: QuickLink[] = [
    {
      title: 'لیست خرابی‌ها',
      subtitle: `${toFaNumber(queues.openFaults)} مورد در انتظار تصمیم توزیع`,
      to: '/faults',
      icon: CarRepair,
      tone: 'warning',
    },
    {
      title: 'کارتابل ترابری',
      subtitle: `${toFaNumber(queues.transportQueue)} مورد در صف ترابری`,
      to: '/repairs',
      icon: Build,
      tone: 'error',
    },
    {
      title: 'لیست خودروها',
      subtitle: `${toFaNumber(vehicleSummary?.active_fleet_count)} خودرو فعال`,
      to: '/vehicles',
      icon: DirectionsCar,
      tone: 'primary',
    },
    {
      title: 'لیست راننده‌ها',
      subtitle: `${toFaNumber(driverSummary?.active_count)} راننده فعال`,
      to: '/drivers',
      icon: PeopleAlt,
      tone: 'success',
    },
    {
      title: 'لاگ SAP',
      subtitle: sapSummary
        ? `${toFaNumber(sapSummary.failed + sapSummary.exhausted)} ناموفق · ${toFaNumber(sapSummary.success)} موفق`
        : 'مشاهده تراکنش‌های SAP',
      to: '/sap',
      icon: Sync,
      tone: 'primary',
    },
  ];

  return (
    <Stack spacing={{ xs: 1.5, md: 2.25 }} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="داشبورد"
        breadcrumbs={[{ label: 'اصلی' }, { label: 'داشبورد' }]}
      />

      <Card
        sx={{
          background: (theme) =>
            `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 55%, ${theme.palette.success.dark} 100%)`,
          color: 'common.white',
          border: 'none',
        }}
      >
        <CardContent sx={{ p: { xs: 2, md: 2.5 }, '&:last-child': { pb: { xs: 2, md: 2.5 } } }}>
          <Typography variant="h2" color="inherit" mb={0.75}>
            نمای کلی ناوگان
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.92, maxWidth: 520 }}>
            وضعیت خودروها، راننده‌ها و صف‌های توزیع و ترابری بر اساس آخرین داده‌های سامانه.
          </Typography>
        </CardContent>
      </Card>

      {error && <ErrorState message={error} onRetry={() => void load()} />}
      {loading && !error && <LoadingState label="در حال بارگذاری داشبورد..." />}

      {!loading && !error && (
        <>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'repeat(2, minmax(0, 1fr))',
                md: 'repeat(4, minmax(0, 1fr))',
              },
              gap: 1.5,
            }}
          >
            <KpiCard
              label="کل ناوگان فعال"
              value={toFaNumber(vehicleSummary?.active_fleet_count)}
              icon={DirectionsCar}
            />
            <KpiCard
              label="عملیاتی"
              value={toFaNumber(vehicleSummary?.operational_fleet_count)}
              icon={TaskAlt}
              tone="success"
            />
            <KpiCard
              label="در تعمیر"
              value={toFaNumber(vehicleSummary?.under_repair_fleet_count)}
              icon={Build}
              tone="warning"
            />
            <KpiCard
              label="خارج از سرویس"
              value={toFaNumber(vehicleSummary?.unusable_fleet_count)}
              icon={ErrorOutline}
              tone="error"
            />
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'repeat(2, minmax(0, 1fr))',
                md: 'repeat(4, minmax(0, 1fr))',
              },
              gap: 1.5,
            }}
          >
            <KpiCard
              label="راننده فعال"
              value={toFaNumber(driverSummary?.active_count)}
              icon={PeopleAlt}
              tone="success"
            />
            <KpiCard
              label="راننده با خودرو"
              value={toFaNumber(driverSummary?.with_vehicle_count)}
              icon={DirectionsCar}
              tone="info"
            />
            <KpiCard
              label="میانگین کیلومتر"
              value={toFaNumber(vehicleSummary?.average_odometer_km)}
              icon={Speed}
              tone="info"
            />
            <KpiCard
              label="میانگین خرابی ۳۰ روز"
              value={toFaNumber(vehicleSummary?.average_faults_last_30_days)}
              icon={CarRepair}
              tone="warning"
            />
          </Box>

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
                    <Typography fontWeight={800}>لاگ و همگام‌سازی SAP</Typography>
                    <Typography variant="body2" color="text.secondary">
                      خودرو: {formatDateTime(vehicleSummary?.last_sap_sync_at)} · راننده:{' '}
                      {formatDateTime(driverSummary?.last_sap_sync_at)}
                      {sapSummary
                        ? ` · تراکنش‌ها: ${toFaNumber(sapSummary.total)} (ناموفق: ${toFaNumber(sapSummary.failed + sapSummary.exhausted)})`
                        : ''}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </CardActionArea>
          </Card>
        </>
      )}
    </Stack>
  );
}
