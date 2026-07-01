# WOS-M Owner Manual Test Plan

**Test Date**: ___________________  
**Owner Name**: ___________________  
**Discord Server**: تجارب  
**Bot**: WOS-M

---

## قبل البدء

### المتطلبات
- Discord account مع صلاحية Admin/Owner في سيرفر "تجارب"
- حساب Member عادي للاختبار الثاني
- Bot WOS-M متصل ومتاح

### البنية
```
qa/live-discord/
├── screenshots/
│   ├── 01_wos_dashboard.png
│   ├── 02_alliances_add.png
│   ├── ...
├── logs/
│   └── test_session.log
└── db/
    └── db_summary.md
```

---

## SECTION A: /wos Command Test

### A1. تشغيل /wos
1. افتح Discord
2. ادخل سيرفر "تجارب"
3. اكتب في شات:

```
/wos
```

4. انتظر ظهور Dashboard
5. **صور Dashboard كاملاً**

### معيار القبول
- ✅ Dashboard يظهر بدون تأخير
- ✅ لا يوجد "Interaction Failed"
- ✅ لا يوجد Error
- ✅ أزرار ظاهره

---

## SECTION B: Dashboard Buttons Test

### B1. أزرار التنقل الأساسية
اضغط كل زر وصوّر النتيجة:

| # | Button | Screenshot | Result | PASS/FAIL |
|---|--------|------------|--------|-----------|
| 1 | Alliances | B01_ | | |
| 2 | Players | B02_ | | |
| 3 | Gift Codes | B03_ | | |
| 4 | Events | B04_ | | |
| 5 | Attendance | B05_ | | |
| 6 | Bear Tracking | B06_ | | |
| 7 | Ministers | B07_ | | |
| 8 | Notifications | B08_ | | |
| 9 | Themes | B09_ | | |
| 10 | Permissions | B10_ | | |
| 11 | Maintenance | B11_ | | |
| 12 | Owner Panel | B12_ | | |
| 13 | Language | B13_ | | |
| 14 | Settings | B14_ | | |
| 15 | Back | B15_ | | |
| 16 | Home | B16_ | | |
| 17 | Close | B17_ | | |

### معيار القبول لكل زر
- ✅ الزر يستجيب
- ✅ لا يوجد Interaction Failed
- ✅ المحتوى المناسب يظهر

---

## SECTION C: Alliance Flow Test

### C1. إضافة Alliance
1. اضغط **Alliances**
2. اضغط **Add Alliance**
3. ادخل:
   - Alliance Name: `QA Alliance 1478`
   - State KID: `1478`
   - Discord Role ID: اتركه فارغاً
4. اضغط **Submit**
5. **صور رسالة النجاح**

### C2. عرض Alliance List
1. اضغط **Alliance List**
2. **صور القائمة**
3. تحقق من ظهور `QA Alliance 1478`

### C3. تعديل Alliance
1. اضغط على `QA Alliance 1478`
2. اضغط **Edit**
3. غيّر الاسم إلى: `QA Alliance 1478 Updated`
4. اضغط **Save**
5. **صور رسالة النجاح**

### C4. إعدادات Gift
1. اضغط على `QA Alliance 1478 Updated`
2. اضغط **Gift Settings**
3. **صور الإعدادات**
4. ارجع

### C5. إعدادات Sync
1. اضغط على `QA Alliance 1478 Updated`
2. اضغط **Sync Settings**
3. **صور الإعدادات**
4. ارجع

### C6. حذف Alliance (في النهاية فقط)
1. اضغط على `QA Alliance 1478 Updated`
2. اضغط **Delete**
3. confirm
4. **صور رسالة الحذف**

### معيار القبول
- ✅ Alliance ينضاف
- ✅ يظهر في القائمة
- ✅ التعديل يعمل
- ✅ الإعدادات تفتح
- ✅ الحذف يعمل
- ✅ Audit Log يسجل

---

## SECTION D: Player Flow Test

### D1. إضافة Player
1. اضغط **Players**
2. اضغط **Add Player**
3. ادخل:
   - FID: `524717069`
   - Name: `QA Player`
   - Alliance: `QA Alliance 1478 Updated`
4. اضغط **Submit**
5. **صور رسالة النجاح**

### D2. البحث بالـ FID
1. اضغط **Search**
2. ادخل: `524717069`
3. **صور النتيجة**

### D3. البحث بالاسم
1. اضغط **Search**
2. ادخل: `QA Player`
3. **صور النتيجة**

### D4. عرض القائمة
1. اضغط **List**
2. **صور القائمة**

### D5. تصدير Players
1. اضغط **Export**
2. انتظر ملف CSV/JSON
3. **احفظ الملف في qa/live-discord/db/**

### D6. نقل Player
1. اضغط على `QA Player`
2. اضغط **Move**
3. اختر alliance مختلف
4. **صور النتيجة**
5. ارجعه إلى `QA Alliance 1478 Updated`

### معيار القبول
- ✅ Player ينضاف
- ✅ البحث بالـ FID يعمل
- ✅ البحث بالاسم يعمل
- ✅ القائمة تعرض اللاعب
- ✅ التصدير يرسل ملف
- ✅ النقل يعمل

---

## SECTION E: Gift Codes Test

### E1. إضافة Gift Code
1. اضغط **Gift Codes**
2. اضغط **Add Code**
3. ادخل كود هدية معروف أو مستخدم
4. اضغط **Submit**
5. **صور النتيجة**

### E2. استرداد单一 Code
1. اضغط **Redeem Single**
2. ادخل الكود و FID اللاعب
3. **صور النتيجة**

### E3. استرداد Alliance
1. اضغط **Redeem Alliance**
2. اختر `QA Alliance 1478 Updated`
3. **صور النتيجة**

### E4. تفعيل Auto Redeem
1. اضغط **Auto**
2. اختر `QA Alliance 1478 Updated`
3. فعّل
4. **صور النتيجة**

### E5. تقرير Gift Codes
1. اضغط **Report**
2. **صور التقرير**

### معيار القبول
- ✅ إضافة الكود تعمل
- ✅ الاسترداد يرجع نتيجة (RECEIVED, Already claimed, Error)
- ✅ Auto Redeem يفعل/يغلق
- ✅ Report يعرض الإحصائيات

---

## SECTION F: RBAC Test

### F1. اختبار بحساب Member عادي
1. سجّل دخول بحساب Member
2. جرّب كل عملية:
   - Add Alliance → يجب رفض
   - Delete Alliance → يجب رفض
   - Add Player → يجب رفض
   - Export Players → يجب رفض
   - Owner Panel → يجب رفض
   - Permissions → يجب رفض
   - Maintenance → يجب رفض
   - Redeem Gift → يجب رفض

3. **صور كل رفض**

### F2. اختبار بحساب Admin/Owner
1. سجّل دخول بحساب Admin/Owner
2. جرّب نفس العمليات
3. يجب أن تنجح أو تظهر صفحة التحكم

4. **صور كل نتيجة**

### معيار القبول
- ✅ Member يرفض بدون traceback
- ✅ رسالة واضحة: "ليس لديك صلاحية"
- ✅ Admin/Owner مسموح

---

## SECTION G: Error Handling Test

### G1. مدخلات خاطئة
جرّب وأصور:

| # | Test | Input | Expected |
|---|------|-------|----------|
| 1 | FID قصير | `123` | خطأ واضح |
| 2 | FID طويل | `12345678901234` | خطأ واضح |
| 3 | FID بحروف | `abc123def` | خطأ واضح |
| 4 | Player غير موجود | FID: `999999999` | رسالة واضحة |
| 5 | كود فارغ | `` | خطأ واضح |

### G2. الضغط المتكرر
1. اضغط زر 10 مرات بسرعة
2. **صور النتيجة**

### معيار القبول
- ✅ رسالة خطأ واضحة
- ✅ لا traceback للمستخدم
- ✅ لا crash
- ✅ لا Interaction Failed

---

## SECTION H: Stability Test

### H1. /wos متكرر
1. اكتب `/wos` 10 مرات
2. **صور آخر Dashboard**

### H2. أزرار متكررة
1. افتح/أغلق Alliance List 5 مرات
2. **صور النتيجة**

### معيار القبول
- ✅ لا crash
- ✅ لا error متتالي
- ✅ لا interaction timeout

---

## SECTION I: Database Verification

بعد انتهاء الاختبارات، نفّذ هذه الأوامر:

```bash
# في مجلد المشروع
cd /workspace/project/wos-m

# تشغيل البوت مع الأمر
python main.py --check

# أو استخدم sqlite3
sqlite3 data/wosm.sqlite ".tables"
sqlite3 data/wosm.sqlite "SELECT COUNT(*) FROM alliances;"
sqlite3 data/wosm.sqlite "SELECT COUNT(*) FROM players;"
sqlite3 data/wosm.sqlite "SELECT COUNT(*) FROM audit_logs;"
sqlite3 data/wosm.sqlite "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 10;"
```

**احفظ النتائج في qa/live-discord/db/db_summary.md**

---

## SECTION J: Screenshot Naming Convention

```
qa/live-discord/screenshots/
├── A01_wos_command.png
├── B01_button_alliances.png
├── B02_button_players.png
├── ...
├── C01_alliance_add.png
├── C02_alliance_list.png
├── ...
├── D01_player_add.png
├── ...
├── E01_gift_add.png
├── ...
├── F01_rbac_member_deny.png
├── F02_rbac_admin_allow.png
├── ...
└── Z01_test_complete.png
```

---

## CHECKLIST النهائي

| Section | Status | Screenshots Count |
|---------|--------|------------------|
| A: /wos | ⬜ | ___ |
| B: Buttons | ⬜ | ___ |
| C: Alliance | ⬜ | ___ |
| D: Players | ⬜ | ___ |
| E: Gift Codes | ⬜ | ___ |
| F: RBAC | ⬜ | ___ |
| G: Errors | ⬜ | ___ |
| H: Stability | ⬜ | ___ |
| I: DB | ⬜ | ___ |

**Total Screenshots**: ___

---

## ملخص الاختبار

| البند | النتيجة |
|-------|---------|
| /wos Dashboard | ✅/❌ |
| All Buttons Working | ✅/❌ |
| Alliance CRUD | ✅/❌ |
| Player CRUD | ✅/❌ |
| Gift Codes | ✅/❌ |
| RBAC Enforced | ✅/❌ |
| Error Handling | ✅/❌ |
| Stability | ✅/❌ |
| Audit Logs | ✅/❌ |

---

**© MANSOUR — WOS-M. All rights reserved.**