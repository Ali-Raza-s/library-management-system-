# ============================================================
# Smart-Shelf: Digital Library Manager
# File: app.py
# Purpose: Main Flask application (all routes in one file for viva)
# RBAC: Admin, Librarian, Student — enforced on every protected route
# Database: MySQL only
# Run: python app.py
# ============================================================

import re
from functools import wraps

from flask import Flask, render_template, redirect, url_for, session, request, flash
from werkzeug.security import check_password_hash, generate_password_hash

from database.activity_log import get_recent_logs, log_activity
from database.mysql_connection import connect_database, ensure_schema_tables, ensure_users_created_at_column


app = Flask(__name__)
app.secret_key = "smart_shelf_secret_key_2026"

ensure_users_created_at_column()
ensure_schema_tables()


# ============================================================
# RBAC DECORATORS (viva: backend route protection)
# login_required               -> Admin, Librarian, Student (logged in)
# admin_required               -> Admin only
# librarian_or_admin_required  -> Admin + Librarian
# ============================================================
def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)
    return wrapped_view


def role_required(allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("Please login first.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in allowed_roles:
                flash("You do not have permission to access this feature.", "danger")
                return redirect(url_for("dashboard"))
            return view_function(*args, **kwargs)
        return wrapped_view
    return decorator


def admin_required(view_function):
    return role_required(["Admin"])(view_function)


def librarian_or_admin_required(view_function):
    return role_required(["Admin", "Librarian"])(view_function)


# ============================================================
# PASSWORD HELPERS (werkzeug hashing for security)
# Supports old plain-text passwords until user logs in again
# ============================================================
def is_password_hashed(stored_password):
    return (
        stored_password.startswith("pbkdf2:")
        or stored_password.startswith("scrypt:")
    )


def verify_user_password(stored_password, entered_password):
    if is_password_hashed(stored_password):
        return check_password_hash(stored_password, entered_password)
    return stored_password == entered_password


def hash_password(plain_password):
    return generate_password_hash(plain_password)


def clean_text(value):
    return (value or "").strip()


def has_alpha(text):
    return any(char.isalpha() for char in text)


def is_valid_book_title(title):
    title = clean_text(title)
    if len(title) < 2:
        return False, "Title must be at least 2 characters long."
    if title.isdigit():
        return False, "Title cannot contain only numbers."
    if not has_alpha(title):
        return False, "Title must contain alphabetic characters."
    return True, ""


def is_valid_author_name(author):
    author = clean_text(author)
    if author == "":
        return False, "Author name is required."
    if author.isdigit():
        return False, "Author name cannot be numeric."
    if not has_alpha(author):
        return False, "Author name must contain alphabetic characters."
    return True, ""


def is_valid_isbn(isbn):
    isbn = clean_text(isbn)
    if isbn == "":
        return True, ""
    if not re.fullmatch(r"[0-9-]+", isbn):
        return False, "ISBN must contain only digits and hyphens."
    if not 10 <= len(isbn) <= 17:
        return False, "ISBN length must be between 10 and 17 characters."
    return True, ""


def is_valid_user_name(name):
    name = clean_text(name)
    if name == "":
        return False, "Name is required."
    if name.isdigit():
        return False, "Name cannot contain only numbers."
    if not has_alpha(name):
        return False, "Name must contain alphabetic characters."
    return True, ""


def is_valid_phone_number(phone_number):
    phone_number = clean_text(phone_number)
    if phone_number == "":
        return True, ""
    if not phone_number.isdigit():
        return False, "Phone number must contain digits only."
    if not 7 <= len(phone_number) <= 15:
        return False, "Phone number length is invalid."
    return True, ""


def is_valid_cnic(cnic):
    cnic = clean_text(cnic)
    if cnic == "":
        return True, ""
    if not re.fullmatch(r"\d{5}-\d{7}-\d", cnic):
        return False, "CNIC must follow the format 12345-1234567-1."
    return True, ""


def refresh_overdue_status():
    """Update any active borrow records whose due date has passed to overdue status."""
    db_connection = connect_database()
    if db_connection is None:
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute(
            "UPDATE borrows SET status = 'overdue' WHERE status = 'active' AND due_date < CURDATE()"
        )
        db_connection.commit()
        cursor.close()
        db_connection.close()
    except Exception as error_message:
        print("Overdue refresh error:", error_message)
        if db_connection is not None:
            db_connection.close()


def upgrade_password_if_plaintext(user_id, stored_password, entered_password):
    """After successful plain-text login, save hashed password in MySQL."""
    if is_password_hashed(stored_password):
        return

    db_connection = connect_database()
    if db_connection is None:
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute(
            "UPDATE users SET password = %s WHERE user_id = %s",
            (hash_password(entered_password), user_id)
        )
        db_connection.commit()
        cursor.close()
        db_connection.close()
    except Exception as error_message:
        print("Password upgrade error:", error_message)


# ============================================================
# MYSQL ACTIVITY LOG HELPER
# Logs: login, logout, borrow, return, add/edit/delete book, user actions
# ============================================================
def record_activity(action_type, details, user_id=None, role=None):
    log_activity(
        user_id if user_id is not None else session.get("user_id", 0),
        action_type,
        details,
        request.remote_addr,
        role if role is not None else session.get("role"),
    )


# ============================================================
# MYSQL HELPERS
# ============================================================
def load_categories_from_db(cursor):
    sql = "SELECT category_id, category_name FROM categories ORDER BY category_name"
    cursor.execute(sql)
    return cursor.fetchall()


def get_user_by_session_id():
    """Fetch logged-in user from MySQL using session user_id (profile feature)."""
    user_id = session.get("user_id")
    if user_id is None:
        return None

    db_connection = connect_database()
    if db_connection is None:
        return None

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, name, email, role, cnic, phone_number, address, created_at FROM users WHERE user_id = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()
        cursor.close()
        db_connection.close()
        return user_row
    except Exception as error_message:
        print("Get user by session error:", error_message)
        return None


# ============================================================
# Route: Home (/) — Public
# ============================================================
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    mysql_connection = connect_database()
    mysql_status = "Connected" if mysql_connection is not None else "Not Connected"
    if mysql_connection is not None:
        mysql_connection.close()

    return render_template("home.html", mysql_status=mysql_status)


# ============================================================
# Route: Login (/login) — Public
# ACCESS: Everyone (redirect if already logged in)
# ============================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if email == "" or password == "":
            flash("Please enter email and password.", "danger")
            return redirect(url_for("login"))

        db_connection = connect_database()
        if db_connection is None:
            flash("Database connection failed. Please try again later.", "danger")
            return redirect(url_for("login"))

        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, name, email, role, password FROM users WHERE email = %s",
                (email,)
            )
            user_row = cursor.fetchone()
            cursor.close()
            db_connection.close()

            if user_row is not None and verify_user_password(user_row["password"], password):
                session["user_id"] = user_row["user_id"]
                session["name"] = user_row["name"]
                session["role"] = user_row["role"]

                upgrade_password_if_plaintext(
                    user_row["user_id"], user_row["password"], password
                )

                record_activity(
                    "Login",
                    "User logged in to Smart-Shelf",
                    user_id=user_row["user_id"],
                    role=user_row["role"],
                )

                flash("Login successful! Welcome to Smart-Shelf.", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid email or password. Please try again.", "danger")
            return redirect(url_for("login"))

        except Exception as error_message:
            flash("An error occurred during login.", "danger")
            print("Login error:", error_message)
            return redirect(url_for("login"))

    return render_template("login.html")


# ============================================================
# Route: Dashboard (/dashboard)
# ACCESS: Admin, Librarian, Student
# Widgets change by role (Feature 8)
# ============================================================
@app.route("/dashboard")
@login_required
def dashboard():
    refresh_overdue_status()
    user_role = session.get("role")
    stats = {
        "total_books": 0,
        "total_categories": 0,
        "available_books": 0,
        "active_borrows": 0,
        "overdue_books": 0,
        "total_reviews": 0,
        "total_users": 0,
        "my_active_borrows": 0,
        "my_borrow_count": 0,
    }

    db_connection = connect_database()
    if db_connection is not None:
        try:
            cursor = db_connection.cursor()
            user_id = session.get("user_id")

            cursor.execute("SELECT COUNT(*) FROM books")
            stats["total_books"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM categories")
            stats["total_categories"] = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books")
            stats["available_books"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM borrows WHERE status = 'active'")
            stats["active_borrows"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM borrows WHERE status = 'overdue'")
            stats["overdue_books"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM book_reviews")
            stats["total_reviews"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users")
            stats["total_users"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM borrows WHERE user_id = %s AND status = 'active'",
                (user_id,)
            )
            stats["my_active_borrows"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM borrows WHERE user_id = %s", (user_id,))
            stats["my_borrow_count"] = cursor.fetchone()[0]

            cursor.close()
            db_connection.close()
        except Exception as error_message:
            print("Dashboard stats error:", error_message)

    return render_template(
        "dashboard.html",
        user_name=session.get("name"),
        user_role=user_role,
        stats=stats
    )


# ============================================================
# FEATURE 1: User Profile (/profile)
# ACCESS: Admin, Librarian, Student (own profile only via session)
# ============================================================
@app.route("/profile")
@login_required
def profile():
    user_data = get_user_by_session_id()
    if user_data is None:
        flash("Could not load your profile.", "danger")
        return redirect(url_for("dashboard"))

    return render_template("profile.html", user_data=user_data)


# ============================================================
# FEATURE 2: Change Password (/change_password)
# ACCESS: Admin, Librarian, Student
# ============================================================
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if old_password == "" or new_password == "" or confirm_password == "":
            flash("All password fields are required.", "danger")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        db_connection = connect_database()
        if db_connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for("change_password"))

        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT password FROM users WHERE user_id = %s",
                (session.get("user_id"),)
            )
            user_row = cursor.fetchone()

            if user_row is None:
                flash("User not found.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("change_password"))

            if not verify_user_password(user_row["password"], old_password):
                flash("Old password is incorrect.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("change_password"))

            cursor.execute(
                "UPDATE users SET password = %s WHERE user_id = %s",
                (hash_password(new_password), session.get("user_id"))
            )
            db_connection.commit()
            cursor.close()
            db_connection.close()

            record_activity("Change Password", "User changed their password")
            flash("Password updated successfully!", "success")
            return redirect(url_for("profile"))

        except Exception as error_message:
            flash("Could not update password.", "danger")
            print("Change password error:", error_message)
            return redirect(url_for("change_password"))

    return render_template("change_password.html")


# ============================================================
# Categories — Admin only
# ============================================================
@app.route("/categories")
@admin_required
def categories():
    category_list = []
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.category_id, c.category_name, COUNT(b.book_id) AS total_books
                FROM categories c
                LEFT JOIN books b ON c.category_id = b.category_id
                GROUP BY c.category_id, c.category_name
                ORDER BY c.category_name
            """)
            category_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load categories.", "danger")
            print("Categories list error:", error_message)

    return render_template("categories.html", category_list=category_list)


@app.route("/add_category", methods=["GET", "POST"])
@admin_required
def add_category():
    if request.method == "POST":
        category_name = request.form.get("category_name", "").strip()
        if category_name == "":
            flash("Category name is required.", "danger")
            return redirect(url_for("add_category"))

        db_connection = connect_database()
        if db_connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for("add_category"))

        try:
            cursor = db_connection.cursor()
            cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category_name,))
            db_connection.commit()
            cursor.close()
            db_connection.close()
            flash("Category added successfully!", "success")
            return redirect(url_for("categories"))
        except Exception as error_message:
            flash("Could not add category.", "danger")
            print("Add category error:", error_message)
            return redirect(url_for("add_category"))

    return render_template("add_category.html")


@app.route("/delete_category/<int:category_id>")
@admin_required
def delete_category(category_id):
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("categories"))

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM books WHERE category_id = %s", (category_id,))
        book_count = cursor.fetchone()[0]

        if book_count > 0:
            flash("Cannot delete category. It is used by " + str(book_count) + " book(s).", "danger")
            cursor.close()
            db_connection.close()
            return redirect(url_for("categories"))

        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        db_connection.commit()
        flash("Category deleted successfully!", "success") if cursor.rowcount > 0 else flash("Category not found.", "warning")
        cursor.close()
        db_connection.close()
    except Exception as error_message:
        flash("Could not delete category.", "danger")
        print("Delete category error:", error_message)

    return redirect(url_for("categories"))


# ============================================================
# Books — View: all roles | Add/Edit: Admin+Librarian | Delete: Admin
# ============================================================
@app.route("/books")
@login_required
def books():
    book_list = []
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT b.book_id, b.title, b.author, b.isbn, b.description, b.publication_year,
                       b.total_copies, b.available_copies, c.category_name
                FROM books b
                INNER JOIN categories c ON b.category_id = c.category_id
                ORDER BY b.book_id
            """)
            book_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load books.", "danger")
            print("Books list error:", error_message)

    return render_template("books.html", book_list=book_list, search_query="")


# ============================================================
# FEATURE 3: Search Books (/search_books)
# ACCESS: Admin, Librarian, Student
# Uses SQL LIKE on title, author, ISBN
# ============================================================
@app.route("/search_books")
@login_required
def search_books():
    title = request.args.get("title", "").strip()
    author = request.args.get("author", "").strip()
    isbn = request.args.get("isbn", "").strip()

    book_list = []
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)

            sql_query = """
                SELECT b.book_id, b.title, b.author, b.isbn, b.description, b.publication_year,
                       b.total_copies, b.available_copies, c.category_name
                FROM books b
                INNER JOIN categories c ON b.category_id = c.category_id
                WHERE 1=1
            """
            params = []

            if title != "":
                sql_query += " AND b.title LIKE %s"
                params.append("%" + title + "%")

            if author != "":
                sql_query += " AND b.author LIKE %s"
                params.append("%" + author + "%")

            if isbn != "":
                sql_query += " AND b.isbn LIKE %s"
                params.append("%" + isbn + "%")

            sql_query += " ORDER BY b.book_id"
            cursor.execute(sql_query, tuple(params))
            book_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Search failed.", "danger")
            print("Search books error:", error_message)

    search_query = {"title": title, "author": author, "isbn": isbn}
    return render_template("search_books.html", book_list=book_list, search_query=search_query)


@app.route("/add_book", methods=["GET", "POST"])
@librarian_or_admin_required
def add_book():
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("books"))

    if request.method == "POST":
        title = clean_text(request.form.get("title", ""))
        author = clean_text(request.form.get("author", ""))
        isbn = clean_text(request.form.get("isbn", ""))
        description = clean_text(request.form.get("description", ""))
        publication_year = clean_text(request.form.get("publication_year", ""))
        total_copies = request.form.get("total_copies", "1")
        available_copies = request.form.get("available_copies", "1")
        category_id = request.form.get("category_id", "")

        if title == "" or author == "" or category_id == "":
            flash("Title, Author, and Category are required.", "danger")
            return redirect(url_for("add_book"))

        valid_title, title_error = is_valid_book_title(title)
        if not valid_title:
            flash(title_error, "danger")
            return redirect(url_for("add_book"))

        valid_author, author_error = is_valid_author_name(author)
        if not valid_author:
            flash(author_error, "danger")
            return redirect(url_for("add_book"))

        valid_isbn, isbn_error = is_valid_isbn(isbn)
        if not valid_isbn:
            flash(isbn_error, "danger")
            return redirect(url_for("add_book"))

        try:
            total_copies = int(total_copies)
            available_copies = int(available_copies)
            category_id = int(category_id)
            publication_year = int(publication_year) if publication_year else None
        except ValueError:
            flash("Copies and publication year must be valid numbers.", "danger")
            return redirect(url_for("add_book"))

        if available_copies > total_copies:
            flash("Available copies cannot be more than total copies.", "danger")
            return redirect(url_for("add_book"))

        try:
            cursor = db_connection.cursor(dictionary=True)
            if isbn != "":
                cursor.execute("SELECT book_id FROM books WHERE isbn = %s", (isbn,))
                if cursor.fetchone() is not None:
                    flash("This ISBN already exists in the system.", "danger")
                    cursor.close()
                    db_connection.close()
                    return redirect(url_for("add_book"))

            cursor.execute("""
                INSERT INTO books
                (title, author, isbn, description, publication_year, total_copies, available_copies, category_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, author, isbn or None, description or None, publication_year, total_copies, available_copies, category_id))
            db_connection.commit()
            cursor.close()
            db_connection.close()

            record_activity(
                "Add Book",
                "Added book: " + title,
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("Book added successfully!", "success")
            return redirect(url_for("books"))
        except Exception as error_message:
            flash("Could not add book. Check ISBN is unique.", "danger")
            print("Add book error:", error_message)
            return redirect(url_for("add_book"))

    category_list = []
    try:
        cursor = db_connection.cursor(dictionary=True)
        category_list = load_categories_from_db(cursor)
        cursor.close()
        db_connection.close()
    except Exception as error_message:
        flash("Could not load categories.", "danger")
        print("Load categories error:", error_message)

    return render_template("add_book.html", category_list=category_list)


@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
@librarian_or_admin_required
def edit_book(book_id):
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("books"))

    if request.method == "POST":
        title = clean_text(request.form.get("title", ""))
        author = clean_text(request.form.get("author", ""))
        isbn = clean_text(request.form.get("isbn", ""))
        description = clean_text(request.form.get("description", ""))
        publication_year = clean_text(request.form.get("publication_year", ""))
        total_copies = request.form.get("total_copies", "1")
        available_copies = request.form.get("available_copies", "1")
        category_id = request.form.get("category_id", "")

        if title == "" or author == "" or category_id == "":
            flash("Title, Author, and Category are required.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        valid_title, title_error = is_valid_book_title(title)
        if not valid_title:
            flash(title_error, "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        valid_author, author_error = is_valid_author_name(author)
        if not valid_author:
            flash(author_error, "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        valid_isbn, isbn_error = is_valid_isbn(isbn)
        if not valid_isbn:
            flash(isbn_error, "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        try:
            total_copies = int(total_copies)
            available_copies = int(available_copies)
            category_id = int(category_id)
            publication_year = int(publication_year) if publication_year else None
        except ValueError:
            flash("Copies and publication year must be valid numbers.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        if available_copies > total_copies:
            flash("Available copies cannot be more than total copies.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        try:
            cursor = db_connection.cursor(dictionary=True)
            if isbn != "":
                cursor.execute("SELECT book_id FROM books WHERE isbn = %s AND book_id != %s", (isbn, book_id))
                if cursor.fetchone() is not None:
                    flash("Another book already uses this ISBN.", "danger")
                    cursor.close()
                    db_connection.close()
                    return redirect(url_for("edit_book", book_id=book_id))

            cursor.execute("""
                UPDATE books SET title=%s, author=%s, isbn=%s, description=%s, publication_year=%s,
                total_copies=%s, available_copies=%s, category_id=%s
                WHERE book_id=%s
            """, (title, author, isbn or None, description or None, publication_year, total_copies, available_copies, category_id, book_id))
            db_connection.commit()
            cursor.close()
            db_connection.close()
            record_activity(
                "Edit Book",
                "Updated book: " + title,
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("Book updated successfully!", "success")
            return redirect(url_for("books"))
        except Exception as error_message:
            flash("Could not update book.", "danger")
            print("Edit book error:", error_message)
            return redirect(url_for("edit_book", book_id=book_id))

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book_data = cursor.fetchone()
        if book_data is None:
            flash("Book not found.", "warning")
            cursor.close()
            db_connection.close()
            return redirect(url_for("books"))
        category_list = load_categories_from_db(cursor)
        cursor.close()
        db_connection.close()
        return render_template("edit_book.html", book_data=book_data, category_list=category_list)
    except Exception as error_message:
        flash("Could not load book.", "danger")
        print("Edit book load error:", error_message)
        return redirect(url_for("books"))


@app.route("/delete_book/<int:book_id>")
@admin_required
def delete_book(book_id):
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("books"))

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
        book_row = cursor.fetchone()

        cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
        db_connection.commit()

        if cursor.rowcount > 0 and book_row is not None:
            record_activity(
                "Delete Book",
                "Deleted book: " + book_row["title"],
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("Book deleted successfully!", "success")
        else:
            flash("Book not found.", "warning")

        cursor.close()
        db_connection.close()
    except Exception as error_message:
        flash("Cannot delete this book. It may have borrow records.", "danger")
        print("Delete book error:", error_message)

    return redirect(url_for("books"))


# ============================================================
# FEATURE 4 & 5: Borrow / Return — Admin + Librarian only
# Route: /borrow_book and /borrow_book/<book_id>
# Student: NOT allowed (backend enforced)
# ============================================================
@app.route("/borrow_book", methods=["GET", "POST"], defaults={"book_id": None})
@app.route("/borrow_book/<int:book_id>", methods=["GET", "POST"])
@librarian_or_admin_required
def borrow_book(book_id=None):
    refresh_overdue_status()
    if request.method == "POST":
        user_id = request.form.get("user_id", "")
        form_book_id = request.form.get("book_id", "")
        due_date = request.form.get("due_date", "")

        if form_book_id == "" and book_id is not None:
            form_book_id = str(book_id)

        if user_id == "" or form_book_id == "" or due_date == "":
            flash("Please select student, book, and due date.", "danger")
            return redirect(url_for("borrow_book", book_id=book_id) if book_id else url_for("borrow_book"))

        try:
            user_id = int(user_id)
            form_book_id = int(form_book_id)
        except ValueError:
            flash("Invalid student or book selection.", "danger")
            return redirect(url_for("borrow_book"))

        db_connection = connect_database()
        if db_connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for("borrow_book"))

        try:
            cursor = db_connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT user_id, name FROM users WHERE user_id = %s AND role = 'Student'",
                (user_id,)
            )
            student_row = cursor.fetchone()
            if student_row is None:
                flash("Student not found.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("borrow_book"))

            cursor.execute(
                "SELECT book_id, title, available_copies FROM books WHERE book_id = %s",
                (form_book_id,)
            )
            book_row = cursor.fetchone()
            if book_row is None:
                flash("Book not found.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("borrow_book"))

            if book_row["available_copies"] <= 0:
                flash("This book is not available.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("borrow_book"))

            cursor.execute("""
                INSERT INTO borrows (user_id, book_id, borrow_date, due_date, return_date, status)
                VALUES (%s, %s, CURDATE(), %s, NULL, 'active')
            """, (user_id, form_book_id, due_date))

            cursor.execute(
                "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = %s",
                (form_book_id,)
            )

            db_connection.commit()
            cursor.close()
            db_connection.close()

            record_activity(
                "Borrow Book",
                student_row["name"] + " borrowed " + book_row["title"],
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("Book issued successfully.", "success")
            return redirect(url_for("borrows"))

        except Exception as error_message:
            flash("Could not issue book.", "danger")
            print("Borrow book error:", error_message)
            return redirect(url_for("borrow_book"))

    student_list = []
    available_book_list = []
    selected_book_id = book_id
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, name FROM users WHERE role = 'Student' ORDER BY name"
            )
            student_list = cursor.fetchall()
            cursor.execute("""
                SELECT book_id, title, available_copies FROM books
                WHERE available_copies > 0 ORDER BY title
            """)
            available_book_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load borrow form.", "danger")
            print("Borrow form load error:", error_message)

    return render_template(
        "borrow_book.html",
        student_list=student_list,
        available_book_list=available_book_list,
        selected_book_id=selected_book_id
    )


@app.route("/borrows")
@librarian_or_admin_required
def borrows():
    refresh_overdue_status()
    active_borrow_list = []
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                       bk.title AS book_title, br.borrow_date, br.due_date, br.status
                FROM borrows br
                INNER JOIN users u ON br.user_id = u.user_id
                INNER JOIN books bk ON br.book_id = bk.book_id
                WHERE br.status = 'active'
                ORDER BY br.borrow_id DESC
            """)
            active_borrow_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load active borrows.", "danger")
            print("Active borrows error:", error_message)

    return render_template("borrows.html", active_borrow_list=active_borrow_list)


@app.route("/return_book/<int:borrow_id>")
@librarian_or_admin_required
def return_book(borrow_id):
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("borrows"))

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT br.borrow_id, br.book_id, br.status, bk.title AS book_title "
            "FROM borrows br INNER JOIN books bk ON br.book_id = bk.book_id "
            "WHERE br.borrow_id = %s",
            (borrow_id,)
        )
        borrow_row = cursor.fetchone()

        if borrow_row is None:
            flash("Borrow record not found.", "warning")
            cursor.close()
            db_connection.close()
            return redirect(url_for("borrows"))

        if borrow_row["status"] not in ("active", "overdue"):
            flash("This book was already returned.", "info")
            cursor.close()
            db_connection.close()
            return redirect(url_for("borrows"))

        cursor.execute(
            "UPDATE borrows SET return_date = CURDATE(), status = 'returned' WHERE borrow_id = %s",
            (borrow_id,)
        )
        cursor.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE book_id = %s",
            (borrow_row["book_id"],)
        )
        db_connection.commit()
        cursor.close()
        db_connection.close()

        record_activity(
            "Return Book",
            "Returned " + borrow_row["book_title"],
            user_id=session.get("user_id"),
            role=session.get("role"),
        )
        flash("Book returned successfully.", "success")

    except Exception as error_message:
        flash("Could not return book.", "danger")
        print("Return book error:", error_message)

    return redirect(url_for("borrows"))


@app.route("/overdue")
@librarian_or_admin_required
def overdue():
    refresh_overdue_status()
    overdue_list = []
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                       bk.title AS book_title, br.borrow_date, br.due_date,
                       DATEDIFF(CURDATE(), br.due_date) AS days_overdue
                FROM borrows br
                INNER JOIN users u ON br.user_id = u.user_id
                INNER JOIN books bk ON br.book_id = bk.book_id
                WHERE br.status = 'overdue'
                ORDER BY br.due_date ASC
            """)
            overdue_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load overdue books.", "danger")
            print("Overdue error:", error_message)

    return render_template("overdue.html", overdue_list=overdue_list)


# ============================================================
# FEATURE 6: My Borrow History (/my_borrows)
# ACCESS: Student (own only), Admin + Librarian (all records)
# ============================================================
@app.route("/my_borrows")
@login_required
def my_borrows():
    refresh_overdue_status()
    borrow_list = []
    user_role = session.get("role")
    user_id = session.get("user_id")
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)

            if user_role == "Student":
                cursor.execute("""
                    SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                           bk.title AS book_title, br.borrow_date, br.due_date, br.return_date, br.status
                    FROM borrows br
                    INNER JOIN users u ON br.user_id = u.user_id
                    INNER JOIN books bk ON br.book_id = bk.book_id
                    WHERE br.user_id = %s
                    ORDER BY br.borrow_id DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                           bk.title AS book_title, br.borrow_date, br.due_date, br.return_date, br.status
                    FROM borrows br
                    INNER JOIN users u ON br.user_id = u.user_id
                    INNER JOIN books bk ON br.book_id = bk.book_id
                    ORDER BY br.borrow_id DESC
                """)

            borrow_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load borrow records.", "danger")
            print("My borrows error:", error_message)

    return render_template(
        "my_borrows.html",
        borrow_list=borrow_list,
        user_role=user_role,
        view_mode="history"
    )


@app.route("/my_borrowed_books")
@login_required
def my_borrowed_books():
    refresh_overdue_status()
    borrow_list = []
    user_role = session.get("role")
    user_id = session.get("user_id")
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            if user_role == "Student":
                cursor.execute("""
                    SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                           bk.title AS book_title, br.borrow_date, br.due_date, br.return_date, br.status
                    FROM borrows br
                    INNER JOIN users u ON br.user_id = u.user_id
                    INNER JOIN books bk ON br.book_id = bk.book_id
                    WHERE br.user_id = %s AND br.status IN ('active', 'overdue')
                    ORDER BY br.borrow_id DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                           bk.title AS book_title, br.borrow_date, br.due_date, br.return_date, br.status
                    FROM borrows br
                    INNER JOIN users u ON br.user_id = u.user_id
                    INNER JOIN books bk ON br.book_id = bk.book_id
                    WHERE br.status IN ('active', 'overdue')
                    ORDER BY br.borrow_id DESC
                """)

            borrow_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load borrowed books.", "danger")
            print("My borrowed books error:", error_message)

    return render_template(
        "my_borrows.html",
        borrow_list=borrow_list,
        user_role=user_role,
        view_mode="active"
    )


@app.route("/my_overdue")
@login_required
def my_overdue():
    refresh_overdue_status()
    borrow_list = []
    user_role = session.get("role")
    user_id = session.get("user_id")
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            if user_role == "Student":
                cursor.execute("""
                    SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                           bk.title AS book_title, br.borrow_date, br.due_date, br.return_date, br.status
                    FROM borrows br
                    INNER JOIN users u ON br.user_id = u.user_id
                    INNER JOIN books bk ON br.book_id = bk.book_id
                    WHERE br.user_id = %s AND br.status = 'overdue'
                    ORDER BY br.borrow_id DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT br.borrow_id, u.name AS student_name, u.cnic, u.phone_number, u.address,
                           bk.title AS book_title, br.borrow_date, br.due_date, br.return_date, br.status
                    FROM borrows br
                    INNER JOIN users u ON br.user_id = u.user_id
                    INNER JOIN books bk ON br.book_id = bk.book_id
                    WHERE br.status = 'overdue'
                    ORDER BY br.borrow_id DESC
                """)

            borrow_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load overdue books.", "danger")
            print("My overdue error:", error_message)

    return render_template(
        "my_borrows.html",
        borrow_list=borrow_list,
        user_role=user_role,
        view_mode="overdue"
    )


# Legacy route — redirects to my_borrows (no duplicate logic)
@app.route("/history")
@login_required
def history():
    return redirect(url_for("my_borrows"))


@app.route("/book_reviews/<int:book_id>", methods=["GET", "POST"])
@login_required
def book_reviews(book_id):
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("books"))

    if request.method == "POST":
        rating = request.form.get("rating", "").strip()
        review_text = request.form.get("review_text", "").strip()

        if rating == "" or review_text == "":
            flash("Rating and review text are required.", "danger")
            return redirect(url_for("book_reviews", book_id=book_id))

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Rating must be between 1 and 5.", "danger")
            return redirect(url_for("book_reviews", book_id=book_id))

        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT book_id FROM books WHERE book_id = %s", (book_id,))
            if cursor.fetchone() is None:
                cursor.close()
                db_connection.close()
                flash("Book not found.", "warning")
                return redirect(url_for("books"))

            cursor.execute(
                "INSERT INTO book_reviews (book_id, user_id, rating, review_text) VALUES (%s, %s, %s, %s)",
                (book_id, session.get("user_id"), rating, review_text),
            )
            db_connection.commit()
            cursor.close()
            db_connection.close()

            record_activity(
                "Add Review",
                "Added review for book ID " + str(book_id),
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("Review submitted successfully!", "success")
            return redirect(url_for("book_reviews", book_id=book_id))
        except Exception as error_message:
            flash("Could not save review.", "danger")
            print("Review save error:", error_message)
            return redirect(url_for("book_reviews", book_id=book_id))

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT book_id, title, author, description, publication_year FROM books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        if book is None:
            cursor.close()
            db_connection.close()
            flash("Book not found.", "warning")
            return redirect(url_for("books"))

        cursor.execute(
            """
            SELECT br.rating, br.review_text, br.review_date, u.name AS user_name
            FROM book_reviews br
            INNER JOIN users u ON br.user_id = u.user_id
            WHERE br.book_id = %s
            ORDER BY br.review_date DESC
            """,
            (book_id,),
        )
        reviews = cursor.fetchall()
        cursor.close()
        db_connection.close()
        return render_template("book_reviews.html", book=book, reviews=reviews)
    except Exception as error_message:
        flash("Could not load reviews.", "danger")
        print("Load reviews error:", error_message)
        return redirect(url_for("books"))


# ============================================================
# FEATURE 7: Activity Logs (/activity_logs)
# ACCESS: Admin only | Librarian + Student: NOT allowed
# ============================================================
@app.route("/activity_logs")
@admin_required
def activity_logs():
    log_list = get_recent_logs(50)
    return render_template("activity_logs.html", log_list=log_list)


# ============================================================
# Reports — Admin only
# ============================================================
@app.route("/reports")
@admin_required
def reports():
    report_data = {
        "total_books": 0, "total_categories": 0, "total_users": 0,
        "total_students": 0, "total_librarians": 0, "active_borrows": 0,
        "returned_borrows": 0, "overdue_borrows": 0, "available_copies": 0,
    }

    db_connection = connect_database()
    if db_connection is not None:
        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM books")
            report_data["total_books"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM categories")
            report_data["total_categories"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users")
            report_data["total_users"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Student'")
            report_data["total_students"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Librarian'")
            report_data["total_librarians"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM borrows WHERE status = 'active'")
            report_data["active_borrows"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM borrows WHERE status = 'returned'")
            report_data["returned_borrows"] = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM borrows WHERE status = 'overdue'"
            )
            report_data["overdue_borrows"] = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books")
            report_data["available_copies"] = cursor.fetchone()[0]
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load reports.", "danger")
            print("Reports error:", error_message)

    return render_template("reports.html", report_data=report_data)


# ============================================================
# User Management — Admin only
# ============================================================
@app.route("/users")
@admin_required
def users():
    user_list = []
    db_connection = connect_database()

    if db_connection is not None:
        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, name, email, role, cnic, phone_number, address, created_at FROM users ORDER BY user_id"
            )
            user_list = cursor.fetchall()
            cursor.close()
            db_connection.close()
        except Exception as error_message:
            flash("Could not load users.", "danger")
            print("Users list error:", error_message)

    return render_template("users.html", user_list=user_list)


@app.route("/add_user", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        name = clean_text(request.form.get("name", ""))
        email = clean_text(request.form.get("email", ""))
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()
        cnic = clean_text(request.form.get("cnic", ""))
        phone_number = clean_text(request.form.get("phone_number", ""))
        address = clean_text(request.form.get("address", ""))

        if name == "" or email == "" or password == "" or role == "":
            flash("Name, Email, Password, and Role are required.", "danger")
            return redirect(url_for("add_user"))

        if role not in ("Admin", "Librarian", "Student"):
            flash("Invalid role selected.", "danger")
            return redirect(url_for("add_user"))

        valid_name, name_error = is_valid_user_name(name)
        if not valid_name:
            flash(name_error, "danger")
            return redirect(url_for("add_user"))

        valid_cnic, cnic_error = is_valid_cnic(cnic)
        if not valid_cnic:
            flash(cnic_error, "danger")
            return redirect(url_for("add_user"))

        valid_phone, phone_error = is_valid_phone_number(phone_number)
        if not valid_phone:
            flash(phone_error, "danger")
            return redirect(url_for("add_user"))

        db_connection = connect_database()
        if db_connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for("add_user"))

        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone() is not None:
                flash("A user with this email already exists.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("add_user"))

            if cnic != "":
                cursor.execute("SELECT user_id FROM users WHERE cnic = %s", (cnic,))
                if cursor.fetchone() is not None:
                    flash("This CNIC already exists in the system.", "danger")
                    cursor.close()
                    db_connection.close()
                    return redirect(url_for("add_user"))

            if phone_number != "":
                cursor.execute("SELECT user_id FROM users WHERE phone_number = %s", (phone_number,))
                if cursor.fetchone() is not None:
                    flash("This phone number already exists in the system.", "danger")
                    cursor.close()
                    db_connection.close()
                    return redirect(url_for("add_user"))

            cursor.execute(
                "INSERT INTO users (name, email, password, role, cnic, phone_number, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, email, hash_password(password), role, cnic or None, phone_number or None, address or None)
            )
            db_connection.commit()
            cursor.close()
            db_connection.close()
            record_activity(
                "Add User",
                "Created user: " + name,
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("User added successfully!", "success")
            return redirect(url_for("users"))
        except Exception as error_message:
            flash("Could not add user.", "danger")
            print("Add user error:", error_message)
            return redirect(url_for("add_user"))

    return render_template("add_user.html")


@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("users"))

    if request.method == "POST":
        name = clean_text(request.form.get("name", ""))
        email = clean_text(request.form.get("email", ""))
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "").strip()
        cnic = clean_text(request.form.get("cnic", ""))
        phone_number = clean_text(request.form.get("phone_number", ""))
        address = clean_text(request.form.get("address", ""))

        if name == "" or email == "" or role == "":
            flash("Name, Email, and Role are required.", "danger")
            return redirect(url_for("edit_user", user_id=user_id))

        if role not in ("Admin", "Librarian", "Student"):
            flash("Invalid role selected.", "danger")
            return redirect(url_for("edit_user", user_id=user_id))

        valid_name, name_error = is_valid_user_name(name)
        if not valid_name:
            flash(name_error, "danger")
            return redirect(url_for("edit_user", user_id=user_id))

        valid_cnic, cnic_error = is_valid_cnic(cnic)
        if not valid_cnic:
            flash(cnic_error, "danger")
            return redirect(url_for("edit_user", user_id=user_id))

        valid_phone, phone_error = is_valid_phone_number(phone_number)
        if not valid_phone:
            flash(phone_error, "danger")
            return redirect(url_for("edit_user", user_id=user_id))

        try:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s AND user_id != %s",
                (email, user_id)
            )
            if cursor.fetchone() is not None:
                flash("Another user already uses this email.", "danger")
                cursor.close()
                db_connection.close()
                return redirect(url_for("edit_user", user_id=user_id))

            if cnic != "":
                cursor.execute("SELECT user_id FROM users WHERE cnic = %s AND user_id != %s", (cnic, user_id))
                if cursor.fetchone() is not None:
                    flash("Another user already uses this CNIC.", "danger")
                    cursor.close()
                    db_connection.close()
                    return redirect(url_for("edit_user", user_id=user_id))

            if phone_number != "":
                cursor.execute("SELECT user_id FROM users WHERE phone_number = %s AND user_id != %s", (phone_number, user_id))
                if cursor.fetchone() is not None:
                    flash("Another user already uses this phone number.", "danger")
                    cursor.close()
                    db_connection.close()
                    return redirect(url_for("edit_user", user_id=user_id))

            if password != "":
                cursor.execute(
                    "UPDATE users SET name=%s, email=%s, role=%s, cnic=%s, phone_number=%s, address=%s, password=%s WHERE user_id=%s",
                    (name, email, role, cnic or None, phone_number or None, address or None, hash_password(password), user_id)
                )
            else:
                cursor.execute(
                    "UPDATE users SET name=%s, email=%s, role=%s, cnic=%s, phone_number=%s, address=%s WHERE user_id=%s",
                    (name, email, role, cnic or None, phone_number or None, address or None, user_id)
                )

            db_connection.commit()
            cursor.close()
            db_connection.close()
            record_activity(
                "Edit User",
                "Updated user: " + name,
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("User updated successfully!", "success")
            return redirect(url_for("users"))
        except Exception as error_message:
            flash("Could not update user.", "danger")
            print("Edit user error:", error_message)
            return redirect(url_for("edit_user", user_id=user_id))

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, name, email, role, cnic, phone_number, address FROM users WHERE user_id = %s",
            (user_id,)
        )
        user_data = cursor.fetchone()
        cursor.close()
        db_connection.close()
        if user_data is None:
            flash("User not found.", "warning")
            return redirect(url_for("users"))
        return render_template("edit_user.html", user_data=user_data)
    except Exception as error_message:
        flash("Could not load user.", "danger")
        print("Edit user load error:", error_message)
        return redirect(url_for("users"))


@app.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users"))

    db_connection = connect_database()
    if db_connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("users"))

    try:
        cursor = db_connection.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        db_connection.commit()
        if cursor.rowcount > 0:
            record_activity(
                "Delete User",
                "Deleted user ID: " + str(user_id),
                user_id=session.get("user_id"),
                role=session.get("role"),
            )
            flash("User deleted successfully!", "success")
        else:
            flash("User not found.", "warning")
        cursor.close()
        db_connection.close()
    except Exception as error_message:
        flash("Cannot delete user. They may have borrow records.", "danger")
        print("Delete user error:", error_message)

    return redirect(url_for("users"))


# ============================================================
# Route: Logout (/logout)
# ============================================================
@app.route("/logout")
def logout():
    if "user_id" in session:
        record_activity(
            "Logout",
            "User logged out from Smart-Shelf",
            user_id=session.get("user_id"),
            role=session.get("role"),
        )
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
