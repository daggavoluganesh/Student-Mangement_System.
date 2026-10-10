from flask import Blueprint, render_template, session, redirect, request
from db import get_connection

student_bp = Blueprint("student", __name__)

# ================= STUDENT DASHBOARD =================
@student_bp.route("/")
def student_dashboard():
    if "student" not in session:
        return redirect("/login")

    roll_no = session["student"]

    conn = get_connection()
    cursor = conn.cursor()

    # ---------- SUBJECT WISE MARKS ----------
    cursor.execute("""
        SELECT 
            s.roll_no,
            s.name,
            sub.subject_name,
            m.marks
        FROM students s
        JOIN marks m ON s.roll_no = m.roll_no
        JOIN subjects sub ON m.subject_id = sub.subject_id
        WHERE s.roll_no = %s
    """, (roll_no,))
    raw = cursor.fetchall()

    students = []
    for r in raw:
        marks = r[3]
        if marks >= 90:
            grade, result = "S", "Pass"
        elif marks >= 75:
            grade, result = "A", "Pass"
        elif marks >= 60:
            grade, result = "B", "Pass"
        elif marks >= 40:
            grade, result = "C", "Pass"
        else:
            grade, result = "F", "Fail"

        students.append((r[0], r[1], r[2], marks, grade, result))

    # ---------- ATTENDANCE ----------
    cursor.execute("""
        SELECT 
            COUNT(date) AS total_days,
            SUM(status='Present') AS present_days
        FROM attendance
        WHERE roll_no = %s
    """, (roll_no,))

    row = cursor.fetchone()
    total_days = row[0] or 0
    present_days = row[1] or 0

    attendance_percentage = round(
        (present_days / total_days) * 100, 2
    ) if total_days > 0 else 0

    attendance_status = "OK" if attendance_percentage >= 75 else "LOW"

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        students=students,
        attendance_percentage=attendance_percentage,
        attendance_status=attendance_status
    )


# ================= CHANGE PASSWORD =================
@student_bp.route("/student/change-password", methods=["GET", "POST"])
def student_change_password():
    if "student" not in session:
        return redirect("/login")

    if request.method == "POST":
        old = request.form["old_password"]
        new = request.form["new_password"]
        roll_no = session["student"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT password FROM student_login WHERE roll_no=%s",
            (roll_no,)
        )
        current = cursor.fetchone()

        if not current or current[0] != old:
            cursor.close()
            conn.close()
            return render_template(
                "student_change_password.html",
                message="❌ Old password incorrect"
            )

        cursor.execute(
            "UPDATE student_login SET password=%s WHERE roll_no=%s",
            (new, roll_no)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return render_template(
            "student_change_password.html",
            message="✅ Password changed successfully"
        )

    return render_template("student_change_password.html")


# ================= FORGOT PASSWORD =================
@student_bp.route("/student/forgot-password", methods=["GET", "POST"])
def student_forgot_password():
    if request.method == "POST":
        roll_no = request.form["roll_no"]
        new_password = request.form["new_password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM student_login WHERE roll_no=%s",
            (roll_no,)
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return render_template(
                "student_forgot_password.html",
                message="❌ Roll number not found"
            )

        cursor.execute(
            "UPDATE student_login SET password=%s WHERE roll_no=%s",
            (new_password, roll_no)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return render_template(
            "student_forgot_password.html",
            message="✅ Password reset successful"
        )

    return render_template("student_forgot_password.html")