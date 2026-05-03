from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = 'expensecloud_mca_2026_secret'
DB = 'database.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS budget (
        user_id INTEGER PRIMARY KEY,
        amount REAL NOT NULL
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = hash_pw(request.form['password'])
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email=? AND password=?',
            (email, password)
        ).fetchone()
        conn.close()
        if user:
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        error = '❌ Invalid email or password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = hash_pw(request.form['password'])
        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO users (name, email, password) VALUES (?,?,?)',
                (name, email, password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            error = '❌ Email already registered. Try logging in.'
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    conn = get_db()
    expenses = conn.execute(
        'SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC',
        (uid,)
    ).fetchall()
    b = conn.execute('SELECT amount FROM budget WHERE user_id=?', (uid,)).fetchone()
    budget = b['amount'] if b else 60000
    total = sum(e['amount'] for e in expenses)
    conn.close()
    cat_totals = {}
    for e in expenses:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + e['amount']
    top_cat = max(cat_totals, key=cat_totals.get) if cat_totals else '—'
    top_cat_val = cat_totals.get(top_cat, 0)
    return render_template('dashboard.html',
        expenses=expenses, budget=budget,
        total=total, left=budget - total,
        cat_totals=cat_totals,
        top_cat=top_cat, top_cat_val=top_cat_val,
        user_name=session['user_name'])

@app.route('/add', methods=['POST'])
@login_required
def add():
    conn = get_db()
    conn.execute(
        'INSERT INTO expenses (user_id,description,amount,category,date) VALUES (?,?,?,?,?)',
        (session['user_id'], request.form['description'],
         float(request.form['amount']), request.form['category'],
         request.form['date'])
    )
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    conn = get_db()
    conn.execute(
        'DELETE FROM expenses WHERE id=? AND user_id=?',
        (id, session['user_id'])
    )
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/budget', methods=['POST'])
@login_required
def set_budget():
    uid = session['user_id']
    amount = float(request.form['budget'])
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO budget (user_id, amount) VALUES (?,?)',
        (uid, amount)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/expenses')
@login_required
def expenses():
    uid = session['user_id']
    conn = get_db()
    expenses = conn.execute(
        'SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC', (uid,)
    ).fetchall()
    total = sum(e['amount'] for e in expenses)
    conn.close()
    return render_template('expenses.html',
        expenses=expenses, total=total,
        user_name=session['user_name'])

@app.route('/reports')
@login_required
def reports():
    uid = session['user_id']
    conn = get_db()
    expenses = conn.execute(
        'SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC', (uid,)
    ).fetchall()
    total = sum(e['amount'] for e in expenses)
    cat_totals = {}
    for e in expenses:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + e['amount']
    conn.close()
    return render_template('reports.html',
        expenses=expenses, total=total,
        cat_totals=cat_totals,
        user_name=session['user_name'])

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    uid = session['user_id']
    conn = get_db()
    success = None
    error = None
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        new_pw = request.form.get('new_password', '').strip()
        try:
            if new_pw:
                conn.execute(
                    'UPDATE users SET name=?, email=?, password=? WHERE id=?',
                    (name, email, hash_pw(new_pw), uid)
                )
            else:
                conn.execute(
                    'UPDATE users SET name=?, email=? WHERE id=?',
                    (name, email, uid)
                )
            conn.commit()
            session['user_name'] = name
            success = '✅ Profile updated successfully!'
        except:
            error = '❌ Email already in use by another account.'
    user = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    conn.close()
    return render_template('profile.html',
        user=user, success=success, error=error,
        user_name=session['user_name'])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))