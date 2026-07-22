import {useState} from 'react';
import {Navigate, useNavigate} from 'react-router-dom';
import {
    Alert,
    Box,
    Button,
    Checkbox,
    FormControlLabel,
    InputAdornment,
    Stack,
    Typography,
} from '@mui/material';
import {Analytics, DirectionsCar, Lock, Person, PrecisionManufacturing, Sync} from '@mui/icons-material';
import {api, ApiError} from '../../api/client';
import { RtlTextField } from '../../components/RtlTextField';

const featureItems = [
    {label: 'کنترل وضعیت ناوگان و خودروهای عملیاتی', icon: DirectionsCar},
    {label: 'همگام‌سازی زمان‌بندی‌شده با SAP', icon: Sync},
    {label: 'ثبت پیمایش، خرابی و تعمیرات روزانه', icon: PrecisionManufacturing},
    {label: 'داشبورد تحلیلی برای تصمیم‌گیری سریع', icon: Analytics},
];

export function LoginPage() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [remember, setRemember] = useState(true);
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    if (api.getAccessToken()) return <Navigate to="/vehicles" replace/>;

    const submit = async () => {
        setError('');
        setSubmitting(true);
        try {
            const response = await api.login(username, password);
            api.setAuthSession(response);
            navigate('/vehicles', {replace: true});
        } catch (err) {
            if (err instanceof ApiError && err.status === 401) {
                setError('نام کاربری یا رمز عبور صحیح نیست.');
            } else {
                setError(err instanceof Error ? err.message : 'ورود انجام نشد.');
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Box
            sx={{
                minHeight: '100vh',
                display: 'flex',
                bgcolor: '#f4f6f8',
                overflow: 'hidden',
            }}
        >
            <Box
                sx={{
                    display: {xs: 'none', md: 'flex'},
                    flex: '1 1 52%',
                    minHeight: '100vh',
                    position: 'relative',
                    bgcolor: 'primary.dark',
                    color: '#ffffff',
                    alignItems: 'center',
                    justifyContent: 'center',
                    px: {md: 5, lg: 8},
                    py: 6,
                    overflow: 'hidden',
                }}
            >
                <Box
                    sx={{
                        position: 'absolute',
                        width: 260,
                        height: 260,
                        borderRadius: '50%',
                        bgcolor: 'rgba(255,255,255,0.08)',
                        right: -96,
                        bottom: -72,
                    }}
                />
                <Box
                    sx={{
                        position: 'absolute',
                        width: 112,
                        height: 112,
                        borderRadius: '50%',
                        bgcolor: 'rgba(255,255,255,0.08)',
                        left: 64,
                        top: 72,
                    }}
                />
                <Stack
                    spacing={4}
                    alignItems="flex-start"
                    style={{textAlign: 'right', marginLeft: 'auto'}}
                    sx={{width: '100%', maxWidth: 720, position: 'relative', zIndex: 1}}
                >
                    <Stack spacing={1.5} alignItems="flex-start" sx={{width: '100%', textAlign: 'right'}}>

                        <Typography sx={{
                            fontSize: {md: '2rem', lg: '2.35rem'},
                            fontWeight: 900,
                            lineHeight: 1.45,
                            textAlign: 'right'
                        }}>
                            پلتفرم مدیریت هوشمند نگهداری ناوگان
                        </Typography>
                        <Typography sx={{
                            color: 'rgba(255,255,255,0.78)',
                            fontSize: '1rem',
                            lineHeight: 1.9,
                            textAlign: 'right',
                        }}>
                            کنترل خودروها، پیمایش روزانه، خرابی‌ها و تعمیرات با یک جریان متمرکز و قابل اتصال به SAP
                        </Typography>
                    </Stack>

                    <Stack spacing={2.25} alignItems="flex-start" sx={{width: '100%'}}>
                        {featureItems.map((item) => {
                            const Icon = item.icon;
                            return (
                                <Stack key={item.label} direction="row" alignItems="center" spacing={1.5}
                                       sx={{width: '100%', justifyContent: 'flex-start'}}>
                                    <Box
                                        sx={{
                                            width: 36,
                                            height: 36,
                                            borderRadius: (t) => t.radius('xl'),
                                            bgcolor: 'primary.main',
                                            display: 'grid',
                                            placeItems: 'center',
                                            flexShrink: 0,
                                        }}
                                    >
                                        <Icon fontSize="small"/>
                                    </Box>
                                    <Typography sx={{color: 'rgba(255,255,255,0.9)', fontWeight: 700}}>
                                        {item.label}
                                    </Typography>
                                </Stack>
                            );
                        })}
                    </Stack>
                </Stack>
            </Box>
            <Box
                sx={{
                    flex: {xs: '1 1 100%', md: '0 0 48%'},
                    minHeight: '100vh',
                    display: 'grid',
                    placeItems: 'center',
                    px: {xs: 2.5, sm: 5, lg: 8},
                    py: 5,
                    bgcolor: '#ffffff',
                }}
            >
                <Box sx={{width: '100%', maxWidth: 420}}>
                    <Stack spacing={3} style={{direction: 'rtl', textAlign: 'right'}}>
                        <Stack spacing={0.75} alignItems="flex-start">
                            <Typography variant="h1" color="text.primary">
                                ورود به سیستم
                            </Typography>
                        </Stack>

                        {error && <Alert severity="error">{error}</Alert>}

                        <Stack spacing={1.35}>
                            <RtlTextField
                                label="نام کاربری"
                                value={username}
                                onChange={(event) => setUsername(event.target.value)}
                                autoComplete="username"
                                autoFocus
                                fullWidth
                                inputDir="ltr"
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Person fontSize="small"/>
                                        </InputAdornment>
                                    ),
                                }}
                            />
                            <RtlTextField
                                label="رمز عبور"
                                type="password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                autoComplete="current-password"
                                fullWidth
                                inputDir="ltr"
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Lock fontSize="small"/>
                                        </InputAdornment>
                                    ),
                                }}
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter' && username && password) void submit();
                                }}
                            />
                            <FormControlLabel
                                control={<Checkbox checked={remember}
                                                   onChange={(event) => setRemember(event.target.checked)}/>}
                                label="مرا به خاطر بسپار"
                                sx={{
                                    mx: 0,
                                    color: 'text.secondary',
                                    '& .MuiFormControlLabel-label': {fontSize: '0.86rem'}
                                }}
                            />
                            <Button
                                variant="contained"
                                size="large"
                                disabled={!username || !password || submitting}
                                onClick={() => void submit()}
                                sx={{minHeight: 46}}
                            >
                                ورود
                            </Button>
                        </Stack>
                    </Stack>
                </Box>
            </Box>


        </Box>
    );
}
