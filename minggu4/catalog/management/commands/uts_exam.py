"""
UTS Pemrograman Sisi Server - Soal 4 dan Soal 5.

Cara pakai (di dalam container):
    docker compose exec app python manage.py uts_exam --soal 4
    docker compose exec app python manage.py uts_exam --soal 5

Prasyarat:
    python manage.py migrate
    python manage.py seed_demo
    python manage.py generate_performance_data
    python manage.py generate_relationship_data
"""
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from catalog.models import Assignment, Course, Enrollment, Lesson, Submission
from users.models import User


def header(text):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


class Command(BaseCommand):
    help = "Menjalankan seluruh query Soal 4 dan eksperimen Soal 5 UTS PSS"

    def add_arguments(self, parser):
        parser.add_argument("--soal", type=int, choices=[4, 5], required=True)

    def handle(self, *args, **options):
        if options["soal"] == 4:
            self.soal4()
        else:
            self.soal5()

    # ------------------------------------------------------------------
    # SOAL 4
    # ------------------------------------------------------------------
    def soal4(self):
        header("SOAL 4a - Pastikan data tersedia (idempotent)")
        dosen, _ = User.objects.get_or_create(
            username="suprayogi",
            defaults={"email": "suprayogi@gmail.com", "role": User.Role.LECTURER},
        )
        mhs1, _ = User.objects.get_or_create(
            username="fauzan",
            defaults={"email": "fauzan@gmail.com", "role": User.Role.STUDENT},
        )
        mhs2, created = User.objects.get_or_create(
            username="mahasiswa2",
            defaults={"email": "mahasiswa2@gmail.com", "role": User.Role.STUDENT},
        )
        if created:
            mhs2.set_password("12345")
            mhs2.save()

        c1, _ = Course.objects.get_or_create(
            code="PSS01",
            defaults={"title": "Pemrograman Sisi Server", "lecturer": dosen},
        )
        c2, _ = Course.objects.get_or_create(
            code="PSS02",
            defaults={"title": "Basis Data Lanjut", "lecturer": dosen},
        )
        for order, title in enumerate(
            ["Pengenalan Backend", "Pola Arsitektur Backend", "Containerisasi dengan Docker"],
            start=1,
        ):
            Lesson.objects.get_or_create(
                course=c1, order=order, defaults={"title": title, "content": title}
            )
        Enrollment.objects.get_or_create(student=mhs1, course=c1)
        Enrollment.objects.get_or_create(student=mhs2, course=c1)
        a1, _ = Assignment.objects.get_or_create(
            course=c1,
            title="Tugas Django ORM",
            defaults={"deadline": timezone.now() + timedelta(days=7)},
        )
        Submission.objects.get_or_create(
            assignment=a1, student=mhs1, defaults={"content": "Jawaban Django ORM"}
        )

        print(f"Dosen        : {User.objects.filter(role='LECTURER', username='suprayogi').count()} (min 1)")
        print(f"Mahasiswa    : {User.objects.filter(role='STUDENT', username__in=['fauzan','mahasiswa2']).count()} (min 2)")
        print(f"Course       : {Course.objects.filter(code__in=['PSS01','PSS02']).count()} (min 2)")
        print(f"Lesson PSS01 : {Lesson.objects.filter(course=c1).count()} (min 3)")
        print(f"Enrollment   : {Enrollment.objects.filter(course=c1).count()} (min 2)")
        print(f"Assignment   : {Assignment.objects.filter(course=c1).count()} (min 1)")
        print(f"Submission   : {Submission.objects.filter(assignment=a1).count()} (min 1)")

        header("SOAL 4b-1 - Semua Course beserta kode dan judulnya (sampel 5 baris)")
        qs = Course.objects.values_list("code", "title")
        print("Total:", qs.count())
        for code, title in qs[:5]:
            print(f"  {code} - {title}")

        header("SOAL 4b-2 - Course yang diampu seorang dosen (suprayogi)")
        for c in Course.objects.filter(lecturer=dosen)[:5]:
            print(" ", c)
        print("Total:", Course.objects.filter(lecturer=dosen).count())

        header("SOAL 4b-3 - Semua Lesson milik Course PSS01")
        for lesson in Lesson.objects.filter(course=c1):
            print(" ", lesson)

        header("SOAL 4b-4 - Jumlah mahasiswa terdaftar pada Course PSS01")
        print(Enrollment.objects.filter(course=c1).count())

        header("SOAL 4b-5 - Semua Assignment milik Course PSS01")
        for a in Assignment.objects.filter(course=c1):
            print(" ", a)

        header("SOAL 4b-6 - Semua Submission milik Assignment 'Tugas Django ORM'")
        for s in Submission.objects.filter(assignment=a1):
            print(" ", s, "| isi:", s.content)

        header("SOAL 4d - Contoh get(), filter(), all()")
        print("get()   :", Course.objects.get(code="PSS01"))
        print("filter():", list(Course.objects.filter(lecturer=dosen, is_active=True)[:3]))
        print("all()   : total", Course.objects.all().count(), "Course")
        try:
            Course.objects.get(code="TIDAKADA")
        except Course.DoesNotExist:
            print("get() data tidak ada -> Course.DoesNotExist")
        print("filter() data tidak ada ->", list(Course.objects.filter(code="TIDAKADA")))

     # ------------------------------------------------------------------
    # SOAL 5
    # ------------------------------------------------------------------
    def soal5(self):
        total_perf = Course.objects.filter(code__startswith="PERF").count()
        if total_perf < 100:
            print("Data PERF belum ada. Jalankan generate_performance_data dan generate_relationship_data.")
            return
 
        def run(label, fn, show=None):
            start = time.perf_counter()
            with CaptureQueriesContext(connection) as ctx:
                rows = fn()
            elapsed = time.perf_counter() - start
            print(f"{label:<45} data={len(rows):<4} query={len(ctx):<4} waktu={elapsed:.4f}s")
            if show:
                print(f"  Jumlah Course ditampilkan: {len(rows)} (sampel 5 baris pertama)")
                for r in rows[:5]:
                    print("   ", show(r))
            return len(rows), len(ctx), ctx
 
        base = Course.objects.filter(code__startswith="PERF").order_by("code")
 
        header("SOAL 5a - Course + dosen TANPA select_related")
        def before_lect():
            return [(c.title, c.lecturer.username) for c in base[:100]]
        n1, q_before_lect, _ = run(
            "Tanpa select_related", before_lect,
            show=lambda r: f"{r[0]}  |  Dosen: {r[1]}",
        )
 
        header('SOAL 5b - Course + dosen DENGAN select_related("lecturer")')
        def after_lect():
            return [(c.title, c.lecturer.username) for c in base.select_related("lecturer")[:100]]
        _, q_after_lect, ctx = run(
            "Dengan select_related", after_lect,
            show=lambda r: f"{r[0]}  |  Dosen: {r[1]}",
        )
        print("SQL (memakai JOIN):\n ", ctx.captured_queries[0]["sql"][:300], "...")
 
        header('SOAL 5c - Course + Lesson dengan prefetch_related("lessons")')
        def before_lesson():
            return [(c.code, [l.title for l in c.lessons.all()]) for c in base[:50]]
        n2, q_before_lesson, _ = run("Tanpa prefetch_related", before_lesson)
        def after_lesson():
            return [(c.code, [l.title for l in c.lessons.all()]) for c in base.prefetch_related("lessons")[:50]]
        _, q_after_lesson, ctx = run(
            "Dengan prefetch_related", after_lesson,
            show=lambda r: f"{r[0]}  |  Lesson: {', '.join(r[1])}",
        )
        for i, q in enumerate(ctx.captured_queries, 1):
            print(f"  query {i}: {q['sql'][:150]}...")
 
        header("SOAL 5d - QuerySet.explain()")
        print("[1] filter(is_active=True, title=...)  -> ada index (is_active, title)")
        print(Course.objects.filter(is_active=True, title="Performance Course 5000").explain())
        print("\n[2] filter(code='PERF05000') -> kolom unique (ada index otomatis)")
        print(Course.objects.filter(code="PERF05000").explain())
        print("\n[3] filter(description__icontains=...) -> tanpa index (pembanding)")
        print(Course.objects.filter(description__icontains="xyz").explain())
 
        header("TABEL HASIL OPTIMASI (salin ke laporan)")
        print(f"{'Skenario':<20}{'Jumlah Data':<14}{'Query Sebelum':<16}{'Query Sesudah'}")
        print(f"{'Course + Lecturer':<20}{n1:<14}{q_before_lect:<16}{q_after_lect}")
        print(f"{'Course + Lesson':<20}{n2:<14}{q_before_lesson:<16}{q_after_lesson}")
 