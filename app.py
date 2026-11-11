from flask import Flask, render_template, request, jsonify, make_response
import sqlite3
import csv
from io import StringIO
from datetime import datetime

app = Flask(__name__)

DATABASE = "training.db"

# PREDEFINED FICTIONAL TRAINING ACCOUNTS
DEMO_ACCOUNTS = [
    {
        "id": "DEMO-001",
        "email": "demo1@example.com",
        "password": "TrainingDemo123!",
        "label": "Fictional Account 1"
    },
    {
        "id": "DEMO-002",
        "email": "demo2@example.com",
        "password": "CyberDemo456!",
        "label": "Fictional Account 2"
    }
]

# DATABASE CONNECTION
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

# INITIALIZE DATABASE
def initialize_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS training_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            ip_address TEXT,
            created_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_accounts (
            id TEXT PRIMARY KEY,
            fictional_email TEXT NOT NULL,
            fictional_password TEXT NOT NULL,
            label TEXT NOT NULL
        )
    """)

    # Permanently save the predefined fictional accounts.
    for account in DEMO_ACCOUNTS:
        connection.execute("""
            INSERT OR IGNORE INTO demo_accounts
            (id, fictional_email, fictional_password, label)
            VALUES (?, ?, ?, ?)
        """, (
            account["id"],
            account["email"],
            account["password"],
            account["label"]
        ))

    connection.commit()
    connection.close()

# RECORD A CONSENTED TRAINING EVENT
def record_event(event_type, status):
    connection = get_db_connection()

    # Full IP address as seen by the local Flask application.
    visitor_ip = request.remote_addr or "Unavailable"

    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection.execute("""
        INSERT INTO training_events
        (test_id, event_type, status, ip_address, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        "DEMO-001",
        event_type,
        status,
        visitor_ip,
        current_time
    ))

    connection.commit()
    connection.close()

# HOMEPAGE
@app.route("/")
def home():
    return render_template(
        "index.html",
        demo_accounts=DEMO_ACCOUNTS
    )

# RECORD VISIT AFTER CONSENT
@app.route("/record_visit", methods=["POST"])
def record_visit():
    data = request.get_json(silent=True) or {}

    if data.get("consent") is not True:
        return jsonify({
            "message": "Please provide consent first."
        }), 400

    record_event(
        "Awareness page visit",
        "Visitor agreed to the training notice"
    )

    return jsonify({
        "message": "Visit recorded successfully. You can now select a demo account."
    })

# RECORD FICTIONAL ACCOUNT SELECTION
@app.route("/select_account", methods=["POST"])
def select_account():
    data = request.get_json(silent=True) or {}

    if data.get("consent") is not True:
        return jsonify({
            "message": "Consent is required."
        }), 400

    account_id = data.get("account_id")

    connection = get_db_connection()

    account = connection.execute("""
        SELECT * FROM demo_accounts
        WHERE id = ?
    """, (account_id,)).fetchone()

    connection.close()

    if account is None:
        return jsonify({
            "message": "Invalid fictional account."
        }), 400

    record_event(
        "Fictional account selected",
        "Selected email: " + account["fictional_email"]
    )

    return jsonify({
        "message": "Fictional account selection recorded."
    })

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    connection = get_db_connection()

    results = connection.execute("""
        SELECT * FROM training_events
        ORDER BY id DESC
    """).fetchall()

    demo_accounts = connection.execute("""
        SELECT * FROM demo_accounts
        ORDER BY id
    """).fetchall()

    total_events = connection.execute("""
        SELECT COUNT(*) FROM training_events
    """).fetchone()[0]

    total_visits = connection.execute("""
        SELECT COUNT(*) FROM training_events
        WHERE event_type = 'Awareness page visit'
    """).fetchone()[0]

    total_selections = connection.execute("""
        SELECT COUNT(*) FROM training_events
        WHERE event_type = 'Fictional account selected'
    """).fetchone()[0]

    connection.close()

    return render_template(
        "dashboard.html",
        results=results,
        demo_accounts=demo_accounts,
        total_events=total_events,
        total_visits=total_visits,
        total_selections=total_selections
    )

# CSV REPORT EXPORT
@app.route("/export")
def export_report():
    connection = get_db_connection()

    results = connection.execute("""
        SELECT
            id,
            test_id,
            event_type,
            status,
            ip_address,
            created_at
        FROM training_events
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Test ID",
        "Event Type",
        "Status",
        "Full IP Address",
        "Date and Time"
    ])

    for item in results:
        writer.writerow([
            item["id"],
            item["test_id"],
            item["event_type"],
            item["status"],
            item["ip_address"],
            item["created_at"]
        ])

    response = make_response(output.getvalue())

    response.headers["Content-Disposition"] = (
        "attachment; filename=training_report.csv"
    )

    response.headers["Content-Type"] = "text/csv"

    return response

# START APPLICATION
initialize_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
