from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models.db import get_connection
from datetime import date, timedelta

student = Blueprint("student", __name__)

# ------------------ DASHBOARD ------------------
@student.route("/dashboard")
def dashboard():
    if "user_id" not in session or session.get("role") != "student":
        flash("You must log in as a student.", "danger")
        return redirect(url_for("auth.login"))

    return render_template(
        "student/student_dashboard.html",
        student_name=session.get("user_name"),
        student_id=session.get("user_id")
    )

# ------------------ VIEW ALL BOOKS ------------------
@student.route("/view_books")
def view_books():
    if "user_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("auth.login"))

    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM books")
            books = cur.fetchall()
    finally:
        con.close()

    return render_template("student/view_books.html", books=books)

# ------------------ ISSUE BOOK REQUEST ------------------
@student.route("/issue_book", methods=["GET", "POST"])
def issue_book():
    if "user_id" not in session or session.get("role") != "student":
        flash("You must log in as a student.", "danger")
        return redirect(url_for("auth.login"))

    student_id = session["user_id"]
    con = get_connection()
    with con.cursor() as cur:
        # Get all books
        cur.execute("SELECT * FROM books")
        books = cur.fetchall()

        # Get all issue requests of this student
        cur.execute("""
            SELECT ir.*, b.book_name, b.author_name 
            FROM issue_requests ir
            JOIN books b ON ir.book_id = b.book_id
            WHERE ir.student_id=%s
            ORDER BY ir.request_id DESC
        """, (student_id,))
        requests = cur.fetchall()

    con.close()
    return render_template("student/issue_book.html", books=books, requests=requests)

@student.route("/request_issue/<int:book_id>,<int:number>", methods=["POST"])
def request_issue(book_id,number):
    if "user_id" not in session or session.get("role") != "student":
        flash("Login required.", "danger")
        return redirect(url_for("auth.login"))

    student_id = session["user_id"]
    
    con = get_connection()
    cur = con.cursor()
    
    # cur.execute("""
    #         SELECT book_id, number_of_books 
    #         FROM books 
    #         WHERE book_id=%s
    #     """, (book_id))
    # existing = cur.fetchone()
    # bookid = existing[book_id]
    # new_total = existing['number_of_books'] - 1
    with con.cursor() as cur:
        cur.execute("""
                    UPDATE books 
                    SET number_of_books=%s 
                    WHERE book_id=%s
                """, (number-1, book_id))
        cur.execute("""
            INSERT INTO issue_requests (student_id, book_id, status) 
            VALUES (%s, %s, 'Pending')
        """, (student_id, book_id))
        con.commit()
    con.close()
    flash("Book request submitted!", "success")
    return redirect(url_for("student.issue_book"))

# ------------------ SEARCH BOOK ------------------
@student.route("/search_book", methods=["GET", "POST"])
def search_book():
    if "user_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("auth.login"))

    results = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        con = get_connection()
        try:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT * FROM books
                    WHERE book_name LIKE %s OR author_name LIKE %s
                """, (f"%{keyword}%", f"%{keyword}%"))
                results = cur.fetchall()
        finally:
            con.close()

    return render_template("student/search_book.html", results=results, keyword=keyword)

# ------------------ CHANGE PASSWORD ------------------
@student.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        flash("You must be logged in.", "danger")
        return redirect(url_for("auth.login"))

    student_id = session["user_id"]

    if request.method == "POST":
        old_password = request.form.get("old_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm", "").strip()

        if not old_password or not new_password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect(url_for("student.change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("student.change_password"))

        con = get_connection()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT password FROM students WHERE id=%s", (student_id,))
                user = cur.fetchone()
                if not user:
                    flash("User not found.", "danger")
                    return redirect(url_for("student.change_password"))

                if old_password != user["password"]:
                    flash("Old password is incorrect.", "danger")
                    return redirect(url_for("student.change_password"))

                cur.execute("UPDATE students SET password=%s WHERE id=%s", (new_password, student_id))
            con.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("student.dashboard"))
        except Exception as e:
            con.rollback()
            flash("Database error!", "danger")
            return redirect(url_for("student.change_password"))
        finally:
            con.close()

    return render_template("student/change_password.html")
