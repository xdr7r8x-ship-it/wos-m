# خطة الإصلاح الشاملة لمشروع WOS-M

**التاريخ:** 2026-07-02  
**Commit:** `7351354` (محدث بعد إصلاح P0)  
**الفرع:** main

---

## ملخص المشاكل

| الخطوبة | العدد | الحالة |
|---------|-------|--------|
| P0 (مانع للإطلاق) | 1 | ✅ **تم الإصلاح!** |
| P1 (خطير) | 2 | يحتاج إصلاح قبل الإطلاق |
| P2 (متوسط) | 3 | يحتاج إصلاح قبل الإطلاق |
| P3 (تحسين) | 3 | إصلاح مستقبلي |

---

## ~~إصلاحات فورية~~ (تم!)

### ~~P0-1: إصلاح اختبار CI الفاشل~~ ✅

**المشكلة:** `test_settings_load_from_env_reads_dottodenv_values` يفشل لأنه يتوقع token معين لكن `.env` يحتوي على token مختلف.

**الملف:** `tests/test_environment_loading.py`

**الحالة:** ✅ **تم الإصلاح!**

**الإصلاح المُنفذ:**
```python
# تم تحديث الاختبار لاستخدام tmp_path.fixture
# الاختبار يعمل الآن: 244/244 ✅
```

**وقت التنفيذ:** 15 دقيقة

**الاختبار المطلوب بعد الإصلاح:**
```bash
python -m pytest tests/test_environment_loading.py -v
# ✅ PASSED

python -m pytest tests/ -v
# ✅ 244 passed
```

---

## إصلاحات قبل الإطلاق

### P1-1: توحيد نظام الصلاحيات

**المشكلة:** يوجد نسختان من `PermissionLevel`:
- `core/permissions.py`
- `core/interaction_registry.py`

**الملفات المتأثرة:**
- `core/permissions.py`
- `core/interaction_registry.py`
- `core/bot.py`

**الإصلاح المطلوب:**
1. دمج `PermissionLevel` من `interaction_registry.py` في `permissions.py`
2. استخدام Enum واحد في كل مكان
3. حذف التكرار

**وقت التنفيذ:** 2 ساعة

**الاختبار المطلوب:**
```bash
python -m pytest tests/test_role_visibility_matrix.py -v
```

---

### P1-2: إضافة Rate Limiting

**المشكلة:** لا يوجد rate limiting لـ API calls، مما يسمح بـ DOS.

**الملفات المتأثرة:**
- `integrations/gift_code_client.py`
- `integrations/wos_api_client.py`
- `core/process_queue.py`

**الإصلاح المطلوب:**
1. إضافة `@RateLimiter` decorator
2. تطبيق على API calls
3. إضافة `429 Too Many Requests` handling

**وقت التنفيذ:** 3 ساعات

**الاختبار المطلوب:**
```bash
python -m pytest tests/test_rate_limit.py -v
```

---

### P2-1: إضافة Handlers المفقودة

**المشكلة:** الأزرار `settings_save` و `settings_reset` بدون handlers.

**الملفات المتأثرة:**
- `core/bot.py`
- `modules/settings/views.py` (إن وجد)

**الإصلاح المطلوب:**
```python
# في core/bot.py
async def _handle_settings_save(self, interaction):
    """Handle settings save button."""
    # TODO: تنفيذ الحفظ
    pass

async def _handle_settings_reset(self, interaction):
    """Handle settings reset button."""
    # TODO: تنفيذ إعادة التعيين
    pass
```

**وقت التنفيذ:** 1 ساعة

**الاختبار المطلوب:**
```bash
python -m pytest tests/test_all_interactions_are_routed.py -v
```

---

### P2-2: تصحيح مسار قاعدة البيانات في CI

**المشكلة:** مسار `DATABASE_URL=sqlite:///` غير صحيح.

**الملف:** `.github/workflows/ci.yml`

**الإصلاح المطلوب:**
```yaml
# تغيير من:
DATABASE_URL=sqlite:///data/wosm.sqlite

# إلى:
DATABASE_URL=sqlite:///data/wosm.sqlite
# أو استخدام مسار مطلق للمجلد المؤقت
```

**وقت التنفيذ:** 15 دقيقة

**الاختبار المطلوب:**
```bash
# تشغيل CI محلياً إن أمكن
# أو التحقق من Logs
```

---

### P2-3: إضافة اختبارات التكامل

**المشكلة:** لا توجد اختبارات تكامل للـ integrations.

**الملفات المطلوبة:**
- `tests/test_gift_code_client.py`
- `tests/test_wos_api_client.py`
- `tests/test_captcha_service.py`

**الإصلاح المطلوب:**
```python
# اختبار مع API mock
# اختبار error handling
# اختبار rate limiting
```

**وقت التنفيذ:** 4 ساعات

**الاختبار المطلوب:**
```bash
python -m pytest tests/test_*integration*.py -v
```

---

## تحسينات مستقبلية

### P3-1: إضافة Healthcheck للـ Docker

**الملف:** `Dockerfile`

**الإصلاح المطلوب:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"
```

**وقت التنفيذ:** 30 دقيقة

---

### P3-2: إكمال التوثيق

**المشكلة:** نقص في توثيق API والتطبيق.

**الملفات المطلوبة:**
- `docs/API.md`
- `docs/DEPLOYMENT.md`
- `docs/CONTRIBUTING.md`

**وقت التنفيذ:** 4 ساعات

---

### P3-3: إضافة Monitoring

**المشكلة:** لا يوجد monitoring في الإنتاج.

**الملفات المتأثرة:**
- `core/bot.py`
- `core/metrics.py` (جديد)

**الإصلاح المطلوب:**
1. إضافة Prometheus metrics
2. إضافة health endpoint
3. إضافة alerting

**وقت التنفيذ:** 6 ساعات

---

## ترتيب التنفيذ الصحيح

```
1. P0-1: إصلاح الاختبار (15 دقيقة)
   ↓
2. P2-1: إضافة Handlers (1 ساعة)
   ↓
3. P1-1: توحيد الصلاحيات (2 ساعة)
   ↓
4. P1-2: Rate Limiting (3 ساعات)
   ↓
5. P2-2: تصحيح CI (15 دقيقة)
   ↓
6. P2-3: اختبارات التكامل (4 ساعات)
   ↓
7. P3-1: Docker Healthcheck (30 دقيقة)
   ↓
8. P3-2: التوثيق (4 ساعات)
   ↓
9. P3-3: Monitoring (6 ساعات)
```

**إجمالي الوقت التقريبي:** 21 ساعة

---

## ملخص التنفيذ

| الأولوية | المهمة | الوقت | الملفات |
|----------|---------|-------|---------|
| P0 | إصلاح الاختبار | 15 د | `tests/test_environment_loading.py` |
| P2 | Handlers المفقودة | 1 س | `core/bot.py` |
| P1 | توحيد الصلاحيات | 2 س | `core/permissions.py`, `core/interaction_registry.py` |
| P1 | Rate Limiting | 3 س | `integrations/*` |
| P2 | تصحيح CI | 15 د | `.github/workflows/ci.yml` |
| P2 | اختبارات التكامل | 4 س | `tests/` |
| P3 | Docker Healthcheck | 30 د | `Dockerfile` |
| P3 | التوثيق | 4 س | `docs/` |
| P3 | Monitoring | 6 س | `core/` |

---

## أوامر التحقق النهائية

```bash
# بعد كل إصلاح، تشغيل:
python -m compileall . -q
python -m flake8 core modules integrations views tests main.py
python -m mypy core modules integrations views main.py
python -m pytest tests/ -v --tb=short
python main.py --check
```

---

## الشروط النهائية للإطلاق

1. ✅ جميع اختبارات CI تمر
2. ✅ جميع الأزرار لها handlers
3. ✅ نظام الصلاحيات موحد
4. ✅ Rate limiting مطبق
5. ✅ Docker healthcheck موجود
6. ✅ توثيق كامل

---

## الملفات التي تحتاج تعديل

| الملف | التعديل |
|-------|---------|
| `tests/test_environment_loading.py` | إصلاح الاختبار |
| `core/bot.py` | إضافة handlers + توحيد |
| `core/permissions.py` | دمج مع Registry |
| `core/interaction_registry.py` | حذف التكرار |
| `.github/workflows/ci.yml` | تصحيح المسار |
| `Dockerfile` | إضافة healthcheck |
| `tests/` | إضافة اختبارات تكامل |
| `docs/` | إكمال التوثيق |

---

**نهاية خطة الإصلاح**
