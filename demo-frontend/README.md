# نمایش عملیاتی FMMS — فرانت‌اند مستقل (فارسی RTL)

دمو **زنده** گردش کار نگهداری ناوگان با API واقعی بک‌اند.

این پوشه بخشی از بک‌اند نیست و می‌توان آن را حذف کرد:

```bash
rm -rf demo-frontend
```

## مسیر گردش کار

```text
ورود
  → انتخاب خودرو
  → ثبت بازرسی
  → ثبت خرابی
  → بررسی واحد توزیع
  → تایید ترابری
  → انتخاب تعمیرگاه
```

## فناوری

- HTML / CSS / JavaScript خالص
- Bootstrap 5 RTL + فونت Vazirmatn (CDN)
- بدون React / Vue / ابزار build

## ساختار

```text
demo-frontend/
├── index.html
├── config/env.js       # API_BASE_URL
├── js/api.js           # تمام فراخوانی‌های HTTP
├── js/workflow.js      # وضعیت گردش کار
├── js/app.js           # رندر رابط کاربری
├── css/style.css
└── README.md
```

## پیکربندی

فقط `config/env.js` را ویرایش کنید:

```js
window.FMMS_CONFIG = {
  API_BASE_URL: "http://localhost:8000/api/v1",
  DEMO_MODE: false,
};
```

## اجرا

```bash
cd demo-frontend
python3 -m http.server 5500
```

سپس در مرورگر: `http://localhost:5500`

### پیش‌نیاز بک‌اند

1. سرور FMMS روی پورت `8000`
2. CORS برای `http://localhost:5500` فعال باشد
3. کاربر با نقش مناسب (مثلاً ADMIN یا SUPERVISOR) برای تأیید ترابری
4. قبل از دمو، خودرو و قالب چک‌لیست را از SAP mock همگام کنید:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fmms.test","password":"..."}'

# با توکن:
curl -X POST http://localhost:8000/api/v1/vehicles/sync-sap/ \
  -H "Authorization: Bearer <token>"

curl -X POST http://localhost:8000/api/v1/inspection-templates/sync-sap/ \
  -H "Authorization: Bearer <token>"
```

## صفحات (state جدا)

| صفحه | APIها |
|------|--------|
| **پنل راننده** | `POST /inspections/` سپس `POST /inspections/{id}/submit/` |
| **پنل توزیع** | `GET /faults/` — `POST /faults/{id}/close/` یا `POST /vehicles/{id}/deactivate/` |
| **پنل ترابری** | `GET /repair-orders/` — `POST .../approve/` — `POST .../assign-workshop/` |

`submit` بازرسی **فقط** در پنل راننده فراخوانی می‌شود.
هر صفحه state و پیام/خطای خود را در `sessionStorage` جدا نگه می‌دارد.

### نکته دمو

پس از ثبت بازرسی با آیتم «خراب»، بک‌اند خودکار خرابی و دستور تعمیر می‌سازد. در این حالت ممکن است `deactivate` به‌دلیل وجود دستور تعمیر فعال خطا بدهد؛ در این صورت از پنل ترابری ادامه دهید.

## معماری فرانت

- تمام متن‌های UI فارسی است
- فراخوانی API فقط در `js/api.js`
- وضعیت گردش کار فقط در `js/workflow.js`
- رندر UI فقط در `js/app.js`
