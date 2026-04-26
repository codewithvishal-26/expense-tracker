from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os

app = Flask(__name__)
DB = 'database.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS budget (
        id INTEGER PRIMARY KEY,
        amount REAL NOT NULL
    )''')
    if not conn.execute('SELECT * FROM budget').fetchone():
        conn.execute('INSERT INTO budget VALUES (1, 60000)')
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    conn = get_db()
    expenses = conn.execute('SELECT * FROM expenses ORDER BY date DESC').fetchall()
    budget = conn.execute('SELECT amount FROM budget WHERE id=1').fetchone()[0]
    total = sum(e['amount'] for e in expenses)
    conn.close()
    cat_totals = {}
    for e in expenses:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + e['amount']
    return render_template('dashboard.html',
        expenses=expenses, budget=budget,
        total=total, left=budget-total,
        cat_totals=cat_totals)

@app.route('/add', methods=['POST'])
def add():
    conn = get_db()
    conn.execute('INSERT INTO expenses (description,amount,category,date) VALUES (?,?,?,?)',
        (request.form['description'], float(request.form['amount']),
         request.form['category'], request.form['date']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/budget', methods=['POST'])
def set_budget():
    conn = get_db()
    conn.execute('UPDATE budget SET amount=? WHERE id=1', (float(request.form['budget']),))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))