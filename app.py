from flask import Flask, render_template, request, jsonify
import mysql.connector
import pandas as pd
import numpy as np
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Temporary storage for credentials and uploaded file
db_credentials = {}
uploaded_excel_path = None


# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/creation')
def creation():
    return render_template('creation.html')


# ---------------- STEP 1: CONNECT TO DATABASE ----------------
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


# ---------------- STEP 2: UPLOAD EXCEL FILE ----------------
@app.route('/upload', methods=['POST'])
def upload_excel():
    global uploaded_excel_path
    file = request.files.get('file')

    if not file:
        return jsonify({'status': 'error', 'message': '❌ Please select an Excel file!'})

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


# ---------------- STEP 3: CREATE / RELOAD TABLE ----------------
@app.route('/create_table', methods=['POST'])
def create_table():
    global uploaded_excel_path
    table_name = request.form.get('table_name')
    action = request.form.get('action')  # "reload" or None

    if not table_name:
        return jsonify({'status': 'error', 'message': '❌ Please enter a table name!'})
    if not uploaded_excel_path:
        return jsonify({'status': 'error', 'message': '⚠️ Please upload Excel first!'})

    try:
        df = pd.read_excel(uploaded_excel_path)

        # Auto-detect SQL data types
        def detect_sql_type(series):
            if pd.api.types.is_integer_dtype(series):
                return "INT"
            elif pd.api.types.is_float_dtype(series):
                return "FLOAT"
            elif pd.api.types.is_bool_dtype(series):
                return "BOOLEAN"
            elif pd.api.types.is_datetime64_any_dtype(series):
                return "DATETIME"
            else:
                return "VARCHAR(255)"

        columns_with_types = [f"`{col}` {detect_sql_type(df[col])}" for col in df.columns]

        conn = mysql.connector.connect(**db_credentials)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        table_exists = cursor.fetchone()

        if table_exists and action != "reload":
            return jsonify({
                'status': 'exists',
                'message': f'Table "{table_name}" already exists. Do you want to reload data?'
            })

        # If reload, clear existing data
        if table_exists and action == "reload":
            cursor.execute(f"DELETE FROM `{table_name}`")
            conn.commit()

        # If table doesn’t exist, create it
        if not table_exists:
            create_query = f"CREATE TABLE `{table_name}` ({', '.join(columns_with_types)});"
            cursor.execute(create_query)
            conn.commit()

        # Insert rows into table
        for _, row in df.iterrows():
            values = []
            for val in row:
                if pd.isna(val):
                    values.append(None)
                elif isinstance(val, (np.int64, np.float64)):
                    values.append(val)
                elif isinstance(val, (datetime, pd.Timestamp)):
                    values.append(val.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(val) else None)
                else:
                    values.append(str(val))

            placeholders = ", ".join(["%s"] * len(values))
            insert_query = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
            cursor.execute(insert_query, tuple(values))

        conn.commit()
        cursor.close()
        conn.close()

        if action == "reload":
            return jsonify({'status': 'success', 'message': f'✅ Table "{table_name}" reloaded successfully with {len(df)} rows!'})
        else:
            return jsonify({'status': 'success', 'message': f'✅ Table "{table_name}" created successfully with {len(df)} rows!'})

    except mysql.connector.Error as err:
        return jsonify({'status': 'error', 'message': f'⚠️ MySQL Error: {err}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'⚠️ Error: {str(e)}'})


# ---------------- ERROR HANDLER ----------------
@app.errorhandler(404)
def notfound(e):
    return "<h3>404 - Page Not Found</h3>", 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
