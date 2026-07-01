# WOS-M Database Summary

**Date**: ___________________  
**Owner**: ___________________

---

## DB Commands

Run these commands in the project directory:

```bash
cd /workspace/project/wos-m
sqlite3 data/wosm.sqlite ".tables"
```

---

## Table Counts

| Table | Count |
|-------|-------|
| alliances | ___ |
| players | ___ |
| gift_codes | ___ |
| gift_redemptions | ___ |
| audit_logs | ___ |
| permissions | ___ |
| settings | ___ |

---

## Alliances Table

```sql
SELECT * FROM alliances ORDER BY id DESC LIMIT 5;
```

| id | name | state_kid | discord_role_id | created_at |
|----|------|----------|----------------|------------|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

---

## Players Table

```sql
SELECT * FROM players ORDER BY id DESC LIMIT 5;
```

| id | fid | name | alliance_id | created_at |
|----|-----|------|-------------|------------|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

---

## Gift Codes Table

```sql
SELECT * FROM gift_codes ORDER BY id DESC LIMIT 5;
```

| id | code | created_at | is_active |
|----|------|------------|-----------|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

---

## Gift Redemptions Table

```sql
SELECT * FROM gift_redemptions ORDER BY id DESC LIMIT 5;
```

| id | code_id | player_fid | status | redeemed_at |
|----|---------|------------|--------|------------|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

---

## Audit Logs (Last 20)

```sql
SELECT * FROM audit_logs ORDER BY id DESC LIMIT 20;
```

| id | category | action | user_id | details | timestamp |
|----|----------|--------|---------|---------|-----------|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

---

## Export Files

List any exported CSV/JSON files here:

| File Name | Contents | Rows |
|-----------|----------|------|
| | | |
| | | |

---

## Test QA Alliance Row

```sql
SELECT * FROM alliances WHERE name LIKE '%QA Alliance%';
```

| id | name | state_kid | discord_role_id | auto_redeem | created_at |
|----|------|----------|----------------|--------------|------------|
| | | | | | |

---

## Test QA Player Row

```sql
SELECT * FROM players WHERE name LIKE '%QA Player%';
```

| id | fid | name | alliance_id | created_at |
|----|-----|------|-------------|------------|
| | | | | |

---

**© MANSOUR — WOS-M. All rights reserved.**