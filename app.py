from flask import Flask, render_template, request, jsonify
import mysql.connector
import pandas as pd
import numpy as np
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db_credentials = {}
uploaded_excel_path = None


# ---------------- BASIC ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/creation')
def creation():
    return render_template('creation.html')

@app.route('/fallout')
def fallout():
    return render_template('fallout.html')

@app.route('/migration')
def migration():
    return render_template('migration.html')


# ---------------- STEP 1: Connect DB ----------------
@app.route('/connect_db', methods=['POST'])
def connect_db():
    host = request.form.get('host')
    username = request.form.get('username')
    password = request.form.get('password')
    database = request.form.get('database')

    try:
        conn = mysql.connector.connect(
            host=host,
            user=username,
            password=password,
            database=database
        )
        conn.close()

        db_credentials.update({
            "host": host,
            "user": username,
            "password": password,
            "database": database
        })

        return jsonify({'status': 'success', 'message': '✅ Connected successfully!'})
    except mysql.connector.Error as err:
        msg = str(err)
        if "Access denied" in msg:
            return jsonify({'status': 'error', 'message': '❌ Invalid username or password!'})
        elif "Unknown database" in msg:
            return jsonify({'status': 'error', 'message': '❌ Database not found!'})
        elif "Can\'t connect" in msg:
            return jsonify({'status': 'error', 'message': '❌ Unable to reach MySQL server!'})
        else:
            return jsonify({'status': 'error', 'message': f'⚠️ MySQL error: {msg}'})


# ---------------- STEP 2: Upload Excel ----------------
@app.route('/upload', methods=['POST'])
def upload_excel():
    global uploaded_excel_path
    file = request.files.get('file')

    if not file:
        return jsonify({'status': 'error', 'message': '⚠️ Please select an Excel file!'})

    filename = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filename)

    try:
        df = pd.read_excel(filename)
        if df.empty:
            return jsonify({'status': 'error', 'message': '⚠️ Excel file is empty!'})

        uploaded_excel_path = filename
        row_count = len(df)
        column_list = df.columns.tolist()
        col_count = len(column_list)

        return jsonify({
            'status': 'success',
            'message': f'✅ File uploaded successfully! It contains {row_count} rows and {col_count} columns.',
            'rows': row_count,
            'columns': column_list
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'⚠️ Error reading Excel: {str(e)}'})


# ---------------- STEP 3: Create / Reload Table ----------------
@app.route('/create_table', methods=['POST'])
def create_table():
    global uploaded_excel_path
    table_name = request.form.get('table_name')
    action = request.form.get('action')  # reload, skip, or None

    if not table_name:
        return jsonify({'status': 'error', 'message': '⚠️ Please enter a table name!'})
    if not uploaded_excel_path:
        return jsonify({'status': 'error', 'message': '⚠️ Please upload Excel first!'})

    # ✅ If user clicks Skip
    if action == "skip":
        return jsonify({'status': 'skipped', 'message': '⏭️ You skipped this part.'})

    try:
        df = pd.read_excel(uploaded_excel_path)
        df = df.replace({True: 1, False: 0})

        # ✅ Auto-detect MySQL column types
        columns_with_types = []
        for col in df.columns:
            col_data = df[col].dropna()

            if col_data.empty:
                dtype = "VARCHAR(255)"
            elif pd.api.types.is_integer_dtype(col_data):
                dtype = "INT"
            elif pd.api.types.is_float_dtype(col_data):
                dtype = "FLOAT"
            elif pd.api.types.is_datetime64_any_dtype(col_data) or "date" in col.lower():
                dtype = "DATETIME"
            else:
                # For text, prevent 65535 error
                max_len = col_data.astype(str).map(len).max()
                if max_len <= 255:
                    dtype = "VARCHAR(255)"
                elif max_len <= 2000:
                    dtype = "TEXT"
                else:
                    dtype = "LONGTEXT"

            columns_with_types.append(f"`{col}` {dtype}")

        conn = mysql.connector.connect(**db_credentials)
        cursor = conn.cursor()

        # ✅ Check if table exists
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        table_exists = cursor.fetchone()

        if table_exists and not action:
            return jsonify({
                'status': 'exists',
                'message': f'Table "{table_name}" already exists. Do you want to reload or skip?',
                'options': True
            })

        # ✅ If reload, clear old data
        if table_exists and action == "reload":
            cursor.execute(f"DELETE FROM `{table_name}`")
            conn.commit()

        # ✅ Create new table if not exists
        if not table_exists:
            create_query = f"CREATE TABLE `{table_name}` ({', '.join(columns_with_types)});"
            cursor.execute(create_query)
            conn.commit()

        # ✅ Insert rows safely (keep NULLs as is)
        for _, row in df.iterrows():
            values = [None if pd.isna(v) else v for v in row]
            placeholders = ", ".join(["%s"] * len(values))
            insert_query = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
            cursor.execute(insert_query, tuple(values))

        conn.commit()
        cursor.close()
        conn.close()

        msg = (
            f'✅ Table "{table_name}" reloaded successfully with {len(df)} rows!'
            if action == "reload"
            else f'✅ Table "{table_name}" created successfully with {len(df)} rows!'
        )
        return jsonify({'status': 'success', 'message': msg})

    except mysql.connector.Error as err:
        return jsonify({'status': 'error', 'message': f'⚠️ MySQL Error: {err}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'⚠️ Error: {str(e)}'})


# ---------------- ERROR HANDLER ----------------
@app.errorhandler(404)
def notfound(e):
    return render_template('notfound.html'), 404


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
