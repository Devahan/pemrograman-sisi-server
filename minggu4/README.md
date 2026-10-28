# Minggu 4 — Django Framework & ORM (Simple LMS)

Lanjutan dari Minggu 1–3. Praktikum ini membangun **Core LMS Models** menggunakan Django 5 + PostgreSQL yang berjalan sepenuhnya di Docker.

---

## Prasyarat

| Komponen | Keterangan |
|---|---|
| Docker Desktop | Sudah terinstal dan berjalan |
| VS Code | Editor di host Windows |
| Git | Untuk clone & push repository |

---

## Menjalankan Project

```bash
# 1. Clone repository
git clone https://github.com/Devahan/pemrograman-sisi-server.git
cd pemrograman-sisi-server/minggu4

# 2. Buat file .env (jangan di-commit)
# Isi sesuai kebutuhan — lihat contoh di bawah
DB_NAME=lms_db
DB_USER=lms_user
DB_PASSWORD=lms_password

# 3. Build dan jalankan container
docker compose up -d

# 4. Terapkan migration
docker compose exec app python manage.py migrate

# 5. Buat akun admin
docker compose exec app python manage.py createsuperuser
```

Buka **http://localhost:8000/admin** untuk masuk ke Django Admin.

---

## Model LMS

| Model | Keterangan |
|---|---|
| `User` | Custom user dengan role ADMIN / LECTURER / STUDENT |
| `Course` | Mata kuliah yang diampu dosen |
| `Lesson` | Materi di dalam Course |
| `Enrollment` | Relasi Student ↔ Course |
| `Assignment` | Tugas yang diberikan pada Course |
| `Submission` | Pengumpulan tugas oleh Student |

---

## Sample Data (Seed)

Membuat data contoh secara idempotent (aman dijalankan berulang):

```bash
docker compose exec app python manage.py seed_demo
```

Perintah ini membuat: dosen `suprayogi`, mahasiswa `fauzan`, Course PSS01, 3 Lesson, 1 Enrollment, 2 Assignment, dan 2 Submission.

---

## Membuat Dataset Performa (Minggu 5)

Dataset ini digunakan untuk pengujian optimasi query. Jalankan **urut**:

```bash
# Langkah 1 — Generate 10.000 Course
docker compose exec app python manage.py generate_performance_data

# Langkah 2 — Generate data relasi (Enrollment, Lesson, Assignment, Submission)
docker compose exec app python manage.py generate_relationship_data
```

Hasil yang diharapkan setelah kedua perintah selesai:

| Tabel | Jumlah data |
|---|---|
| Course (PERF*) | 10.000 |
| Lecturer simulasi | 5 |
| Student simulasi | 50 |
| Enrollment | 1.000 |
| Lesson | 500 |
| Assignment | 200 |
| Submission | 1.000 |

> **Catatan:** `generate_relationship_data` membutuhkan minimal 100 Course berkode `PERF*`. Jalankan `generate_performance_data` terlebih dahulu.

---

## Mengulang Benchmark (Minggu 5)

Buka Django Shell dari container:

```bash
docker compose exec app python manage.py shell
```

### Checkpoint 1 — Baseline query count

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext
from catalog.models import Course

with CaptureQueriesContext(connection) as ctx:
    rows = list(Course.objects.all())
print("Jumlah Course:", len(rows))
print("Jumlah query SQL:", len(ctx.captured_queries))
```

### BEFORE: N+1 — Course + Lecturer

```python
import time
from django.db import connection
from django.test.utils import CaptureQueriesContext
from catalog.models import Course

start = time.perf_counter()
with CaptureQueriesContext(connection) as ctx:
    result = []
    for course in Course.objects.filter(code__startswith="PERF").order_by("code")[:100]:
        result.append((course.title, course.lecturer.username))
elapsed = time.perf_counter() - start
print("Jumlah Course:", len(result))
print("Jumlah Query SQL:", len(ctx.captured_queries))
print("Waktu eksekusi:", round(elapsed, 4), "detik")
```

### AFTER: select_related

```python
start = time.perf_counter()
with CaptureQueriesContext(connection) as ctx:
    result = []
    for course in Course.objects.filter(code__startswith="PERF").order_by("code").select_related("lecturer")[:100]:
        result.append((course.title, course.lecturer.username))
elapsed = time.perf_counter() - start
print("Jumlah Course:", len(result))
print("Jumlah Query SQL:", len(ctx.captured_queries))
print("Waktu eksekusi:", round(elapsed, 4), "detik")
```

### BEFORE: N+1 — Course + Lesson

```python
with CaptureQueriesContext(connection) as ctx:
    courses = Course.objects.filter(code__startswith="PERF").order_by("code")[:50]
    for course in courses:
        titles = [lesson.title for lesson in course.lessons.all()]
print("Jumlah query BEFORE:", len(ctx.captured_queries))
```

### AFTER: prefetch_related

```python
with CaptureQueriesContext(connection) as ctx:
    courses = Course.objects.filter(code__startswith="PERF").order_by("code").prefetch_related("lessons")[:50]
    for course in courses:
        titles = [lesson.title for lesson in course.lessons.all()]
print("Jumlah query AFTER:", len(ctx.captured_queries))
```

### EXPLAIN — Database Index

```python
# Sebelum index ditambahkan (atau setelah, untuk membandingkan)
from catalog.models import Course
qs = Course.objects.filter(is_active=True, title="Performance Course 5000")
print(qs.explain())
```

---

## Menjalankan Automated Test

```bash
docker compose exec app python manage.py test
```

Minimal 30 test harus lolos (OK).

---

## Struktur Project

```
minggu4/
├── manage.py
├── config/          # Settings, URL, WSGI
├── users/           # Custom User model
├── catalog/
│   ├── models.py    # Course, Lesson, Enrollment, Assignment, Submission
│   ├── admin.py
│   ├── tests.py     # 30 automated tests
│   └── management/commands/
│       ├── seed_demo.py
│       ├── generate_performance_data.py   # 10.000 Course
│       └── generate_relationship_data.py  # Data relasi LMS
├── requirements.txt
├── Dockerfile
├── compose.yaml
└── .env             # ← TIDAK di-commit (ada di .gitignore)
```

---

## Environment Variables (.env)

File `.env` tidak disertakan di repository karena berisi credential. Buat sendiri di folder `minggu4/`:

```
DB_NAME=lms_db
DB_USER=lms_user
DB_PASSWORD=lms_password
```
