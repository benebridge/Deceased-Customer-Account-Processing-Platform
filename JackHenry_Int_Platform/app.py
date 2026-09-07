#!/usr/bin/env python3
"""
Jack Henry Integration Platform - Main Application
Web interface for viewing synced customer, account, and beneficiary data
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime
import json
from jackhenry_client import JackHenryClient, JXChangeClient
from database import DATABASE_PATH, init_database, seed_api_config, get_config, update_config
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database on startup
if not os.path.exists(DATABASE_PATH):
    init_database()
    seed_api_config()

@app.route('/')
def index():
    """Dashboard showing all synced data"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get customers count
    c.execute('SELECT COUNT(*) as count FROM customers')
    customers_count = c.fetchone()['count']

    # Get accounts count
    c.execute('SELECT COUNT(*) as count FROM accounts')
    accounts_count = c.fetchone()['count']

    # Get beneficiaries count
    c.execute('SELECT COUNT(*) as count FROM beneficiaries')
    beneficiaries_count = c.fetchone()['count']

    # Get recent sync log
    c.execute('''
        SELECT * FROM sync_log
        ORDER BY sync_date DESC
        LIMIT 10
    ''')
    recent_syncs = c.fetchall()

    # Check if API is configured
    client_id = get_config('client_id')
    api_configured = client_id != 'YOUR_CLIENT_ID'

    conn.close()

    return render_template('dashboard.html',
                         customers_count=customers_count,
                         accounts_count=accounts_count,
                         beneficiaries_count=beneficiaries_count,
                         recent_syncs=recent_syncs,
                         api_configured=api_configured)

@app.route('/customers')
def customers():
    """View all customers"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT * FROM customers
        ORDER BY last_synced DESC
    ''')
    customers_list = c.fetchall()

    conn.close()

    return render_template('customers.html', customers=customers_list)

@app.route('/customer/<customer_id>')
def customer_detail(customer_id):
    """View customer details with accounts and beneficiaries"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get customer
    c.execute('SELECT * FROM customers WHERE customer_id = ?', (customer_id,))
    customer = c.fetchone()

    if not customer:
        return "Customer not found", 404

    # Get accounts
    c.execute('SELECT * FROM accounts WHERE customer_sub = ?', (customer['sub'],))
    accounts = c.fetchall()

    # Get beneficiaries for all accounts
    account_ids = [acc['account_id'] for acc in accounts]
    if account_ids:
        placeholders = ','.join('?' * len(account_ids))
        c.execute(f'SELECT * FROM beneficiaries WHERE account_id IN ({placeholders})', account_ids)
        beneficiaries = c.fetchall()
    else:
        beneficiaries = []

    # Parse address JSON
    address = None
    if customer['address_json']:
        address = json.loads(customer['address_json'])

    conn.close()

    return render_template('customer_detail.html',
                         customer=customer,
                         address=address,
                         accounts=accounts,
                         beneficiaries=beneficiaries)

@app.route('/accounts')
def accounts():
    """View all accounts"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT a.*, c.full_name as customer_name
        FROM accounts a
        LEFT JOIN customers c ON a.customer_sub = c.sub
        ORDER BY a.last_synced DESC
    ''')
    accounts_list = c.fetchall()

    conn.close()

    return render_template('accounts.html', accounts=accounts_list)

@app.route('/beneficiaries')
def beneficiaries():
    """View all beneficiaries"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT b.*, a.account_number, a.account_type, c.full_name as account_holder
        FROM beneficiaries b
        LEFT JOIN accounts a ON b.account_id = a.account_id
        LEFT JOIN customers c ON a.customer_sub = c.sub
        ORDER BY b.last_synced DESC
    ''')
    beneficiaries_list = c.fetchall()

    conn.close()

    return render_template('beneficiaries.html', beneficiaries=beneficiaries_list)

@app.route('/config')
def config():
    """API configuration page"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM api_config ORDER BY config_key')
    configs = c.fetchall()

    conn.close()

    return render_template('config.html', configs=configs)

@app.route('/config/update', methods=['POST'])
def update_configuration():
    """Update API configuration"""
    for key, value in request.form.items():
        if key.startswith('config_'):
            config_key = key.replace('config_', '')
            update_config(config_key, value)

    return redirect(url_for('config'))

@app.route('/auth/login')
def auth_login():
    """Initiate OAuth login flow"""
    client = JackHenryClient()
    auth_url, state, code_verifier = client.generate_authorization_url()

    # Store state and code_verifier in session for verification
    session['oauth_state'] = state
    session['code_verifier'] = code_verifier

    return redirect(auth_url)

@app.route('/callback')
def oauth_callback():
    """OAuth callback handler"""
    # Verify state
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        return "Invalid state parameter", 400

    # Get authorization code
    code = request.args.get('code')
    if not code:
        error = request.args.get('error')
        error_desc = request.args.get('error_description', '')
        return f"Authorization failed: {error} - {error_desc}", 400

    try:
        # Get code_verifier from session
        code_verifier = session.get('code_verifier')
        if not code_verifier:
            return "Missing code_verifier in session", 400

        # Exchange code for tokens
        client = JackHenryClient()
        token_data = client.exchange_code_for_tokens(code, code_verifier)

        # Save customer from ID token
        customer_id = client.save_customer_from_token(token_data)

        if customer_id:
            # Extract sub from ID token
            claims = client.decode_id_token(token_data.get('id_token'))
            customer_sub = claims.get('sub')

            # Save tokens
            client.save_tokens(customer_sub, token_data)

            # Sync accounts
            sync_result = client.sync_customer_accounts(customer_sub)

            return redirect(url_for('customer_detail', customer_id=customer_id))
        else:
            return "Failed to extract customer information", 500

    except Exception as e:
        return f"Error during OAuth callback: {str(e)}", 500

@app.route('/sync/<customer_sub>')
def sync_customer(customer_sub):
    """Manually trigger sync for a customer"""
    try:
        client = JackHenryClient()
        result = client.sync_customer_accounts(customer_sub)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/export/customers')
def export_customers():
    """Export all customers as JSON"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM customers')
    customers = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify(customers)

@app.route('/export/accounts')
def export_accounts():
    """Export all accounts as JSON"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM accounts')
    accounts = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify(accounts)

@app.route('/export/beneficiaries')
def export_beneficiaries():
    """Export all beneficiaries as JSON"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM beneficiaries')
    beneficiaries = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify(beneficiaries)

@app.route('/export/all')
def export_all():
    """Export complete database as JSON"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    data = {}

    # Customers
    c.execute('SELECT * FROM customers')
    data['customers'] = [dict(row) for row in c.fetchall()]

    # Accounts
    c.execute('SELECT * FROM accounts')
    data['accounts'] = [dict(row) for row in c.fetchall()]

    # Beneficiaries
    c.execute('SELECT * FROM beneficiaries')
    data['beneficiaries'] = [dict(row) for row in c.fetchall()]

    # Transactions
    c.execute('SELECT * FROM transactions')
    data['transactions'] = [dict(row) for row in c.fetchall()]

    # Sync log
    c.execute('SELECT * FROM sync_log')
    data['sync_log'] = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5012, debug=True)
