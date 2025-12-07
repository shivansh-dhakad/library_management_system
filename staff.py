# controllers/staff.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models.db import get_connection
from datetime import date, timedelta
import random


staff = Blueprint("staff", __name__)

# ---------------- DASHBOARD ----------------
@staff.route("/staff/dashboard")
def dashboard():
    if "user_id" not in session or session.get("role") != "staff":
        flash("You must log in as a staff.", "danger")
        return redirect(url_for("auth.login"))

    return render_template(
        "staff/staff_dashboard.html",
        staff_name=session.get("user_name"),
        staff_id=session.get("user_id")
    )

# -----------------add books--------------------
@staff.route("/add_book", methods=["GET", "POST"])
def add_book():
    if "user_id" not in session or session.get("role") != "staff":
        flash("You must log in as a staff.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        book_name = request.form.get("book_name")
        author_name = request.form.get("author_name")
        publication_year = request.form.get("publication_year")
        number_of_books = int(request.form.get("number_of_books"))

        conn = get_connection()
        cur = conn.cursor()

        # Check if the book already exists (same name + author)
        cur.execute("""
            SELECT book_id, number_of_books 
            FROM books 
            WHERE book_name=%s AND author_name=%s
        """, (book_name, author_name))
        existing = cur.fetchone()

        if existing:
            # Book exists → update number_of_books
            book_id = existing['book_id']
            new_total = existing['number_of_books'] + number_of_books
            cur.execute("""
                UPDATE books 
                SET number_of_books=%s 
                WHERE book_id=%s
            """, (new_total, book_id))
            message = f"Book already exists! Updated total copies to {new_total}."
        else:
            # Book does not exist → insert new
            book_id = random.randint(10000, 99999)
            cur.execute("""
                INSERT INTO books (book_id, book_name, author_name, publication_year, number_of_books)
                VALUES (%s, %s, %s, %s, %s)
            """, (book_id, book_name, author_name, publication_year, number_of_books))
            message = f"Book added successfully! Book ID: {book_id}"

        conn.commit()
        cur.close()
        conn.close()

        return render_template("staff/add_book.html", message=message)

    # GET request
    return render_template("staff/add_book.html")



# ---------------- VIEW ALL BOOKS ----------------
@staff.route("/staff/view_books")
def view_books():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM books")
            books = cur.fetchall()
    finally:
        conn.close()
    
    return render_template("staff/view_books.html", books=books)



# ---------------- REMOVE BOOK ----------------
@staff.route("/remove_book")
def remove_book_page():
    if "user_id" not in session or session.get("role") != "staff":
        flash("Login required.", "danger")
        return redirect(url_for("auth.login"))

    filter_type = request.args.get("filter_type", "all")
    selected_year = request.args.get("year", "").strip()
    selected_limit = request.args.get("limit", "").strip()
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM books WHERE 1"
    params = []

    # ---------- SEARCH ----------
    if search:
        query += " AND (book_id = %s OR book_name LIKE %s OR author_name LIKE %s)"
        params.extend([
            search if search.isdigit() else -1,
            f"%{search}%",
            f"%{search}%"
        ])
    if filter_type == "lowstock":
        query += " AND number_of_books <= 2"

    elif filter_type == "year" and selected_year:
        query += " AND publication_year = %s"
        params.append(selected_year)

    elif filter_type == "limit" and selected_limit.isdigit():
        query += f" LIMIT {int(selected_limit)}"

    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(query, tuple(params))
            books = cur.fetchall()
    finally:
        con.close()

    return render_template(
        "staff/remove_book.html",
        books=books,
        filter_type=filter_type,
        selected_year=selected_year,
        selected_limit=selected_limit,
        search=search
    )

@staff.route("/delete_book/<int:book_id>")
def delete_book(book_id):
    if "user_id" not in session or session.get("role") != "staff":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))

    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
        con.commit()
        flash("Book deleted successfully!", "success")
    except:
        con.rollback()
        flash("Error deleting book.", "danger")
    finally:
        con.close()

    return redirect(url_for("staff.remove_book_page"))


@staff.route("/delete_book_copies/<int:book_id>", methods=["POST"])
def delete_book_copies(book_id):
    if "user_id" not in session or session.get("role") != "staff":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))

    delete_type = request.form.get("delete_type")
    qty = request.form.get("qty")

    con = get_connection()
    try:
        with con.cursor() as cur:

            # Fetch current quantity
            cur.execute("SELECT number_of_books FROM books WHERE book_id=%s", (book_id,))
            book = cur.fetchone()

            if not book:
                flash("Book not found.", "danger")
                return redirect(url_for("staff.remove_book_page"))

            current_qty = book["number_of_books"]

            # Case 1: Delete ALL copies
            if delete_type == "all":
                cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
                flash("All copies deleted!", "success")

            # Case 2: Delete N copies
            else:
                qty = int(qty)

                if qty <= 0:
                    flash("Invalid quantity.", "danger")
                    return redirect(url_for("staff.remove_book_page"))

                if qty >= current_qty:
                    # If N >= total → delete whole book
                    cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
                    flash("Removed all copies (book deleted).", "info")
                else:
                    new_qty = current_qty - qty
                    cur.execute(
                        "UPDATE books SET number_of_books=%s WHERE book_id=%s",
                        (new_qty, book_id)
                    )
                    flash(f"Removed {qty} copies. New quantity: {new_qty}", "success")

            con.commit()

    except Exception as e:
        con.rollback()
        flash("Error updating quantity.", "danger")
    finally:
        con.close()

    return redirect(url_for("staff.remove_book_page"))


# ---------------- VIEW & APPROVE ISSUE REQUESTS ----------------
@staff.route("/staff/issue_requests")
def issue_requests():
    if "user_id" not in session or session.get("role") != "staff":
        flash("Login required.", "danger")
        return redirect(url_for("auth.login"))

    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT 
                    ir.request_id, 
                    ir.status, 
                    ir.approval_date, 
                    ir.due_date,
                    s.name AS student_name,
                    b.book_name
                FROM issue_requests ir
                JOIN students s ON ir.student_id = s.id
                JOIN books b ON ir.book_id = b.book_id
                ORDER BY ir.request_id DESC
            """)
            requests = cur.fetchall()
    finally:
        con.close()

    return render_template("staff/issue_requests.html", requests=requests)



# ---------------- APPROVE REQUEST ----------------
@staff.route("/staff/approve_request/<int:req_id>", methods=["POST"])
def approve_request(req_id):
    today = date.today()
    due_date = today + timedelta(days=10)

    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE issue_requests
                SET status='Approved', approval_date=%s, due_date=%s
                WHERE request_id=%s
            """, (today, due_date, req_id))
            con.commit()

        flash("Request approved!", "success")
    except:
        con.rollback()
        flash("Database error!", "danger")
    finally:
        con.close()

    return redirect(url_for("staff.issue_requests"))


# ---------------- REJECT REQUEST ----------------
@staff.route("/staff/reject_request/<int:req_id>", methods=["POST"])
def reject_request(req_id):
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE issue_requests
                SET status='Rejected'
                WHERE request_id=%s
            """, (req_id,))
            con.commit()

        flash("Request rejected!", "info")
    except:
        con.rollback()
        flash("Error!", "danger")
    finally:
        con.close()

    return redirect(url_for("staff.issue_requests"))

@staff.route("/return_books")
def return_book_page():
    if "user_id" not in session or session.get("role") != "staff":
        flash("Login required.", "danger")
        return redirect(url_for("auth.login"))

    search = request.args.get("search", "").strip()

    con = get_connection()
    try:
        with con.cursor() as cur:
            query = """
                SELECT ir.request_id, ir.status, s.name AS student_name, 
                       b.book_name, ir.book_id
                FROM issue_requests ir
                JOIN students s ON ir.student_id = s.id
                JOIN books b ON ir.book_id = b.book_id
                WHERE ir.status IN ('Approved', 'Returned')
            """

            params = []

            if search:
                query += """
                    AND (
                        ir.request_id = %s OR
                        s.name LIKE %s OR
                        b.book_name LIKE %s
                    )
                """
                params.extend([search if search.isdigit() else -1,
                               f"%{search}%", f"%{search}%"])

            query += " ORDER BY ir.request_id DESC"

            cur.execute(query, tuple(params))
            requests = cur.fetchall()

    finally:
        con.close()

    return render_template("staff/return_books.html", requests=requests)
@staff.route("/return_book/<int:req_id>", methods=["POST"])
def return_book(req_id):

    today = date.today()

    con = get_connection()
    try:
        with con.cursor() as cur:

            # Fetch request
            cur.execute("SELECT * FROM issue_requests WHERE request_id=%s", (req_id,))
            req = cur.fetchone()

            if not req:
                flash("Request not found!", "danger")
                return redirect(url_for("staff.return_book_page"))

            # Update status
            cur.execute("""
                UPDATE issue_requests
                SET status='Returned', return_date=%s
                WHERE request_id=%s
            """, (today, req_id))

            # Increase book stock by 1
            cur.execute("""
                UPDATE books 
                SET number_of_books = number_of_books + 1
                WHERE book_id=%s
            """, (req["book_id"],))

            con.commit()
            flash("Book returned successfully!", "success")

    except Exception as e:
        con.rollback()
        flash("Error: " + str(e), "danger")

    finally:
        con.close()

    return redirect(url_for("staff.return_book_page"))

# ---------------- CHANGE PASSWORD ----------------
@staff.route("/changepassword", methods=["GET", "POST"])
def changepassword():
    if "user_id" not in session:
        flash("You must be logged in.", "danger")
        return redirect(url_for("auth.login"))

    staff_id = session["user_id"]

    if request.method == "POST":
        old_password = request.form.get("old_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm", "").strip()

        if not old_password or not new_password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect(url_for("staff.changepassword"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("staff.changepassword"))

        con = get_connection()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT password FROM staffs WHERE id=%s", (staff_id,))
                user = cur.fetchone()
                if not user:
                    flash("User not found.", "danger")
                    return redirect(url_for("staff.changepassword"))

                if old_password != user["password"]:
                    flash("Old password is incorrect.", "danger")
                    return redirect(url_for("staff.changepassword"))

                cur.execute("UPDATE staffs SET password=%s WHERE id=%s", (new_password, staff_id))
            con.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("staff.dashboard"))
        except Exception as e:
            con.rollback()
            flash("Database error!", "danger")
            return redirect(url_for("staff.changepassword"))
        finally:
            con.close()

    return render_template("staff/change_password.html")
