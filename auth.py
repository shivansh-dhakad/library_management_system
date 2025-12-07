# controllers/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.db import get_connection

auth = Blueprint("auth", __name__)

@auth.route("/", methods=["GET"])
def index():
    return redirect(url_for("auth.login"))

@auth.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user_id = request.form.get("id", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "student")

        if not user_id or not password:
            error = "Enter both ID and password."
            return render_template("login.html", error=error)

        table = "students" if role == "student" else "staff"
        con = get_connection()
        try:
            with con.cursor() as cur:
                cur.execute(f"SELECT * FROM {table} WHERE id=%s", (user_id,))
                user = cur.fetchone()

            if not user:
                error = "Login failed"
                return render_template("login.html", error=error)

            # Plain-text password comparison
            if password == user["password"]:
                session["user_id"] = user_id
                session["role"] = role
                session["user_name"] = user["name"]
                flash("Logged in successfully.", "success")
                if role == "student":
                    return redirect(url_for("student.dashboard"))
                elif role == "staff":
                    return redirect(url_for("staff.dashboard"))
                else:
                    flash("Invalid role!", "danger")
                    return redirect(url_for("auth.login"))
            else:
                error = "Login failed"
                return render_template("login.html", error=error)
        except Exception as e:
            error = "Database error."
            return render_template("login.html", error=error)
        finally:
            con.close()

    return render_template("login.html", error=error)


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        user_id = request.form.get("id", "").strip()
        name = request.form.get("name", "").strip()
        libpass = request.form.get("libpass", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()
        role = request.form.get("role", "student")

        if role=="staff" and libpass != "lib001":
            error = "Invalid library password for staff signup."
            return render_template("signup.html", error=error)
        
        if not user_id or not password or not confirm:
            error = "Fill all required fields."
            return render_template("signup.html", error=error)

        if password != confirm:
            error = "Passwords do not match."
            return render_template("signup.html", error=error)

        table = "students" if role == "student" else "staff"

        con = get_connection()
        try:
            with con.cursor() as cur:
                cur.execute(f"SELECT 1 FROM {table} WHERE id=%s", (user_id,))
                if cur.fetchone():
                    error = "ID already exists."
                    return render_template("signup.html", error=error)

                cur.execute(
                    f"INSERT INTO {table} (id, name, libpass, password) VALUES (%s, %s, %s, %s)",
                    (user_id, name, libpass, password)
                )
                con.commit()

            flash("Signup successful. Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            con.rollback()
            error = "Database error during signup."
            return render_template("signup.html", error=error)
        finally:
            con.close()

    return render_template("signup.html", error=error)


@auth.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
