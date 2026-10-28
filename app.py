import os
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Keep the SQLite database next to this application file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'db.sqlite')

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/input', methods=['GET', 'POST'])
def input_data():
    db = get_db()
    if request.method == 'POST':
        try:
            flower_name = request.form['flower_name']
            type_id = request.form['type_id']
            price = request.form['price']
            description = request.form['description']
            
            client_id = request.form.get('client_id')
            quantity = request.form.get('quantity')
            
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO Flower (FlowerName, TypeID, Price, Description) VALUES (?, ?, ?, ?)",
                (flower_name, type_id, price, description)
            )
            new_flower_id = cursor.lastrowid
            
            if client_id and quantity:
                order_date = datetime.now().strftime('%Y-%m-%d')
                status_id = 1
                total_cost = float(price) * int(quantity)
                employee_id = 5 
                
                cursor.execute('''
                    INSERT INTO Orders (OrderDate, ClientID, EmployeeID, FlowerID, Quantity, Price, StatusID, TotalCost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_date, client_id, employee_id, new_flower_id, quantity, price, status_id, total_cost))
            
            db.commit()
            return render_template('input.html', success="Данные успешно добавлены!", types=get_types(db), clients=get_clients(db))
            
        except Exception as e:
            db.rollback()
            return render_template('input.html', error=f"Ошибка БД: {str(e)}", types=get_types(db), clients=get_clients(db))
        finally:
            db.close()
    
    types = get_types(db)
    clients = get_clients(db)
    db.close()
    return render_template('input.html', types=types, clients=clients)

def get_types(db):
    return db.execute("SELECT TypeID, TypeName FROM FlowerType").fetchall()

def get_clients(db):
    return db.execute("SELECT PersonID, FullName FROM Person WHERE RoleID = 1").fetchall()

@app.route('/search')
def search_page():
    db = get_db()
    types = get_types(db)
    db.close()
    return render_template('search.html', types=types)

@app.route('/api/get_flowers/<int:type_id>')
def api_get_flowers(type_id):
    db = get_db()
    flowers = db.execute("SELECT FlowerID, FlowerName, Price, Description FROM Flower WHERE TypeID = ?", (type_id,)).fetchall()
    db.close()
    result = [dict(row) for row in flowers]
    return jsonify(result)

@app.route('/stats')
def stats():
    db = get_db()
    flowers_count = db.execute("SELECT COUNT(*) FROM Flower").fetchone()[0]
    orders_count = db.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
    
    stats_by_type = db.execute('''
        SELECT FlowerType.TypeName, COUNT(Flower.FlowerID) as count
        FROM FlowerType
        LEFT JOIN Flower ON FlowerType.TypeID = Flower.TypeID
        GROUP BY FlowerType.TypeID
    ''').fetchall()
    
    stats_by_status = db.execute('''
        SELECT OrderStatus.StatusName, COUNT(Orders.OrderID) as count
        FROM OrderStatus
        LEFT JOIN Orders ON OrderStatus.StatusID = Orders.StatusID
        GROUP BY OrderStatus.StatusID
    ''').fetchall()
    
    db.close()
    return render_template('stats.html', 
                           flowers_count=flowers_count, 
                           orders_count=orders_count,
                           stats_by_type=stats_by_type,
                           stats_by_status=stats_by_status)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)