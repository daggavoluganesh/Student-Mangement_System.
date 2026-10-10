from flask import Flask, render_template, request, redirect, session
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp

app = Flask(__name__)
app.secret_key = "student_dashboard_secret"

# Register blueprints
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(student_bp)

# ================= COMMON LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        username = request.form["username"]
        password = request.form["password"]

        from db import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        if role == "student":
            cursor.execute(
                "SELECT * FROM student_login WHERE roll_no=%s AND password=%s",
                (username, password)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session.clear()
                session["student"] = username
                return redirect("/")
            return render_template("login.html", message="Invalid student credentials")

        if role == "admin":
            cursor.execute(
                "SELECT * FROM admin_login WHERE username=%s AND password=%s",
                (username, password)
            )
            admin = cursor.fetchone()
            cursor.close()
            conn.close()

            if admin:
                session.clear()
                session["admin"] = True
                return redirect("/admin")
            return render_template("login.html", message="Invalid admin credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
