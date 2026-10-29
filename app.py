import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "flower-shop-demo-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "db.sqlite")


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_types(db):
    return db.execute(
        "SELECT TypeID, TRIM(TypeName) AS TypeName FROM FlowerType ORDER BY TypeName"
    ).fetchall()


def get_clients(db):
    return db.execute(
        "SELECT PersonID, FullName FROM Person WHERE RoleID = 1 ORDER BY FullName"
    ).fetchall()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/input", methods=["GET", "POST"])
def input_data():
    db = get_db()
    if request.method == "POST":
        try:
            flower_name = request.form["flower_name"].strip()
            type_id = request.form["type_id"]
            price = float(request.form["price"])
            description = request.form["description"].strip()
            client_id = request.form.get("client_id")
            quantity = request.form.get("quantity")

            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO Flower (FlowerName, TypeID, Price, Description) VALUES (?, ?, ?, ?)",
                (flower_name, type_id, price, description),
            )
            new_flower_id = cursor.lastrowid

            if client_id and quantity:
                order_date = datetime.now().strftime("%Y-%m-%d")
                status_id = 1
                total_cost = price * int(quantity)
                employee_id = 5
                cursor.execute(
                    """INSERT INTO Orders
                    (OrderDate, ClientID, EmployeeID, FlowerID, Quantity, Price, StatusID, TotalCost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (order_date, client_id, employee_id, new_flower_id, int(quantity),
                     price, status_id, total_cost),
                )
            db.commit()
            flash("Данные успешно добавлены!", "success")
            return redirect(url_for("input_data"))
        except Exception as exc:
            db.rollback()
            flash(f"Ошибка базы данных: {exc}", "error")
        finally:
            db.close()
        return redirect(url_for("input_data"))

    types = get_types(db)
    clients = get_clients(db)
    db.close()
    return render_template("input.html", types=types, clients=clients)


@app.route("/add-type", methods=["POST"])
def add_type():
    name = request.form.get("type_name", "").strip()
    db = get_db()
    try:
        if len(name) < 3 or len(name) > 50:
            flash("Название типа должно содержать от 3 до 50 символов.", "error")
        else:
            existing = db.execute(
                "SELECT 1 FROM FlowerType WHERE LOWER(TRIM(TypeName)) = LOWER(?)", (name,)
            ).fetchone()
            if existing:
                flash("Такой тип цветка уже существует.", "error")
            else:
                db.execute("INSERT INTO FlowerType (TypeName) VALUES (?)", (name,))
                db.commit()
                flash("Новый тип цветка добавлен.", "success")
    except Exception as exc:
        db.rollback()
        flash(f"Не удалось добавить тип: {exc}", "error")
    finally:
        db.close()
    return redirect(url_for("input_data"))


@app.route("/add-client", methods=["POST"])
def add_client():
    name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip() or None
    email = request.form.get("email", "").strip() or None
    address = request.form.get("address", "").strip() or None
    db = get_db()
    try:
        if len(name) < 10 or len(name) > 60:
            flash("ФИО клиента должно содержать от 10 до 60 символов.", "error")
        else:
            db.execute(
                "INSERT INTO Person (FullName, RoleID, Phone, Email, Address) VALUES (?, 1, ?, ?, ?)",
                (name, phone, email, address),
            )
            db.commit()
            flash("Новый клиент добавлен.", "success")
    except Exception as exc:
        db.rollback()
        flash(f"Не удалось добавить клиента: {exc}", "error")
    finally:
        db.close()
    return redirect(url_for("input_data"))


@app.route("/search")
def search_page():
    db = get_db()
    types = get_types(db)
    client_query = request.args.get("client_q", "").strip()
    clients_found = []
    if client_query:
        pattern = f"%{client_query}%"
        clients_found = db.execute(
            """SELECT PersonID, FullName, Phone, Email, Address
               FROM Person WHERE RoleID = 1
               AND (FullName LIKE ? OR Phone LIKE ? OR Email LIKE ? OR Address LIKE ?)
               ORDER BY FullName""",
            (pattern, pattern, pattern, pattern),
        ).fetchall()
    db.close()
    return render_template("search.html", types=types, client_query=client_query,
                           clients_found=clients_found)


@app.route("/api/get_flowers/<int:type_id>")
def api_get_flowers(type_id):
    db = get_db()
    flowers = db.execute(
        "SELECT FlowerID, FlowerName, Price, Description FROM Flower WHERE TypeID = ?",
        (type_id,),
    ).fetchall()
    db.close()
    return jsonify([dict(row) for row in flowers])


@app.route("/stats")
def stats():
    db = get_db()
    flowers_count = db.execute("SELECT COUNT(*) FROM Flower").fetchone()[0]
    orders_count = db.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
    types_count = db.execute("SELECT COUNT(*) FROM FlowerType").fetchone()[0]
    clients_count = db.execute("SELECT COUNT(*) FROM Person WHERE RoleID = 1").fetchone()[0]
    total_sales = db.execute("SELECT COALESCE(SUM(TotalCost), 0) FROM Orders").fetchone()[0]

    stats_by_type = db.execute("""
        SELECT TRIM(FlowerType.TypeName) AS TypeName, COUNT(Flower.FlowerID) AS count
        FROM FlowerType LEFT JOIN Flower ON FlowerType.TypeID = Flower.TypeID
        GROUP BY FlowerType.TypeID ORDER BY TypeName
    """).fetchall()
    stats_by_status = db.execute("""
        SELECT OrderStatus.StatusName, COUNT(Orders.OrderID) AS count
        FROM OrderStatus LEFT JOIN Orders ON OrderStatus.StatusID = Orders.StatusID
        GROUP BY OrderStatus.StatusID
    """).fetchall()
    db.close()
    return render_template(
        "stats.html", flowers_count=flowers_count, orders_count=orders_count,
        types_count=types_count, clients_count=clients_count, total_sales=total_sales,
        stats_by_type=stats_by_type, stats_by_status=stats_by_status
    )


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
