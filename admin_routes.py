from flask import Blueprint, render_template, session, redirect, request, Response
from db import get_connection
import mysql.connector

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
def marks_to_gp(marks):
    if marks >= 90: return 10
    elif marks >= 80: return 9
    elif marks >= 70: return 8
    elif marks >= 60: return 7
    elif marks >= 50: return 6
    elif marks >= 40: return 5
    else: return 0
# ================= DASHBOARD =================
@admin_bp.route("/")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # SUBJECT-WISE DATA
    cursor.execute("""
        SELECT s.roll_no, s.name, sub.subject_name, m.marks
        FROM students s
        JOIN marks m ON s.roll_no = m.roll_no
        JOIN subjects sub ON m.subject_id = sub.subject_id
        ORDER BY s.roll_no
    """)
    raw = cursor.fetchall()

    students = []
    for r in raw:
        marks = r[3]
        if marks >= 75:
            grade, result = "A", "Pass"
        elif marks >= 40:
            grade, result = "C", "Pass"
        else:
            grade, result = "F", "Fail"

        students.append((r[0], r[1], r[2], marks, grade, result))

    # ✅ STUDENT-WISE SUMMARY
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT roll_no),
            COUNT(DISTINCT CASE 
                WHEN roll_no NOT IN (
                    SELECT roll_no FROM marks WHERE marks < 40
                ) THEN roll_no
            END)
        FROM students
    """)
    total, passed = cursor.fetchone()
    failed = total - passed
    pass_percentage = round((passed / total) * 100, 2) if total > 0 else 0

    cursor.close()
    conn.close()

    return render_template(
        "admin.html",
        students=students,
        total=total,
        passed=passed,
        failed=failed,
        pass_percentage=pass_percentage
    )
# ================= ADD STUDENT =================
@admin_bp.route("/add", methods=["POST"])
def admin_add():
    if "admin" not in session:
        return redirect("/login")

    roll_no = request.form["roll_no"]
    name = request.form["name"]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO students (roll_no, name) VALUES (%s,%s)",
            (roll_no, name)
        )
        cursor.execute(
            "INSERT IGNORE INTO student_login (roll_no, password) VALUES (%s,%s)",
            (roll_no, roll_no)
        )
        conn.commit()
    except mysql.connector.Error:
        pass

    cursor.close()
    conn.close()
    return redirect("/admin")

# ================= DELETE STUDENT =================
@admin_bp.route("/delete", methods=["POST"])
def admin_delete():
    if "admin" not in session:
        return redirect("/login")

    roll_no = request.form["roll_no"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM marks WHERE roll_no=%s", (roll_no,))
    cursor.execute("DELETE FROM students WHERE roll_no=%s", (roll_no,))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect("/admin")

# ================= ATTENDANCE AUTH =================
@admin_bp.route("/attendance-auth", methods=["GET", "POST"])
def attendance_auth():
    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM admin_login WHERE username='admin' AND password=%s",
            (password,)
        )
        ok = cursor.fetchone()
        cursor.close()
        conn.close()

        if ok:
            session["attendance_auth"] = True
            return redirect("/admin/attendance")

        return render_template("attendance_auth.html", message="Wrong password")

    return render_template("attendance_auth.html")

# ================= MARK ATTENDANCE =================
@admin_bp.route("/attendance", methods=["GET", "POST"])
def mark_attendance():
    if "admin" not in session or "attendance_auth" not in session:
        return redirect("/admin/attendance-auth")

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        date = request.form["date"]
        present = request.form.getlist("present")

        cursor.execute("SELECT roll_no FROM students")
        all_students = cursor.fetchall()

        for s in all_students:
            status = "Present" if str(s[0]) in present else "Absent"
            cursor.execute(
                "INSERT INTO attendance (roll_no, date, status) VALUES (%s,%s,%s)",
                (s[0], date, status)
            )

        conn.commit()
        session.pop("attendance_auth", None)

    cursor.execute("SELECT roll_no, name FROM students")
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_attendance.html", students=students)

# ================= ATTENDANCE SUMMARY =================
@admin_bp.route("/attendance-summary")
def attendance_summary():
    if "admin" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.roll_no, s.name,
               COUNT(a.date) total_days,
               SUM(a.status='Present') present_days,
               ROUND((SUM(a.status='Present')/COUNT(a.date))*100,2) percent
        FROM students s
        LEFT JOIN attendance a ON s.roll_no=a.roll_no
        GROUP BY s.roll_no, s.name
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("attendance_summary.html", data=data)
@admin_bp.route("/student-summary")
def student_summary():
    if "admin" not in session:
        return redirect("/login")

    roll_no = request.args.get("roll_no")
    if not roll_no:
        return redirect("/admin")

    conn = get_connection()
    cursor = conn.cursor()

    # ---------------- STUDENT INFO ----------------
    cursor.execute(
        "SELECT roll_no, name FROM students WHERE roll_no=%s",
        (roll_no,)
    )
    student = cursor.fetchone()
    if not student:
        cursor.close()
        conn.close()
        return redirect("/admin")

    # ---------------- SUBJECT MARKS ----------------
    cursor.execute("""
        SELECT sub.subject_name, m.marks
        FROM marks m
        JOIN subjects sub ON m.subject_id = sub.subject_id
        WHERE m.roll_no=%s
    """, (roll_no,))
    subjects = cursor.fetchall()

    # ---------------- CGPA CALCULATION ----------------
    grade_points = []
    total_marks = 0

    for sub in subjects:
        marks = sub[1]
        total_marks += marks
        grade_points.append(marks_to_gp(marks))

    cgpa = round(sum(grade_points) / len(grade_points), 2) if grade_points else 0

    # ---------------- ATTENDANCE ----------------
    cursor.execute("""
        SELECT ROUND((SUM(status='Present') / COUNT(*)) * 100, 2)
        FROM attendance
        WHERE roll_no=%s
    """, (roll_no,))
    attendance = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "admin_student_summary.html",
        student=student,
        subjects=subjects,
        total_marks=total_marks,
        cgpa=cgpa,
        attendance=attendance
    )