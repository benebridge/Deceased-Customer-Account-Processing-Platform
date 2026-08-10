"""
Executour - Unified Inheritance and Estate Settlement Platform
Aggregates data from BeneBridge and other sources to provide comprehensive support
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'executour-secret-key-change-in-production'

# Database path - connects to same DB as BeneBridge
DB_PATH = '../benebridge.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Decorator for routes that require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =================== AUTHENTICATION ===================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # For MVP, simplified authentication - check if email exists in cases
        conn = get_db()

        # Check if there are cases with this beneficiary email
        case = conn.execute(
            'SELECT beneficiary_name, beneficiary_email FROM cases WHERE beneficiary_email = ? LIMIT 1', (email,)
        ).fetchone()

        conn.close()

        if case:
            session['user_email'] = case['beneficiary_email']
            session['user_name'] = case['beneficiary_name']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='No cases found for this email')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

# =================== MAIN DASHBOARD ===================

@app.route('/')
@login_required
def dashboard():
    """Unified Inheritance Dashboard"""
    conn = get_db()
    user_email = session.get('user_email')

    # Get all cases for this user (by beneficiary email)
    cases = conn.execute('''
        SELECT *
        FROM cases
        WHERE beneficiary_email = ?
        ORDER BY submission_date DESC
    ''', (user_email,)).fetchall()

    # Get total inheritance value
    total_inheritance = conn.execute('''
        SELECT COALESCE(SUM(account_balance), 0) as total
        FROM cases
        WHERE beneficiary_email = ?
    ''', (user_email,)).fetchone()['total']

    # For MVP, set mock values for payments and assets
    total_received = 0
    pending_payments = total_inheritance  # Assume all pending for demo

    # Get unclaimed assets count (will be 0 until user searches)
    unclaimed_assets_count = 0

    # Get active tasks count
    active_tasks_result = conn.execute('''
        SELECT COUNT(*) as count FROM estate_tasks
        WHERE status != 'completed'
        LIMIT 1
    ''').fetchone()

    active_tasks = active_tasks_result['count'] if active_tasks_result else 19

    conn.close()

    return render_template('dashboard.html',
                         cases=[dict(c) for c in cases],
                         total_inheritance=total_inheritance,
                         total_received=total_received,
                         pending_payments=pending_payments,
                         unclaimed_assets_count=unclaimed_assets_count,
                         active_tasks=active_tasks)

# =================== UNCLAIMED ASSET DISCOVERY ===================

@app.route('/unclaimed-assets')
@login_required
def unclaimed_assets():
    """Unclaimed Asset Discovery Dashboard"""
    conn = get_db()
    user_id = session.get('user_id')

    # Get unclaimed assets
    assets = conn.execute('''
        SELECT * FROM unclaimed_assets
        WHERE user_id = ?
        ORDER BY estimated_value DESC
    ''', (user_id,)).fetchall()

    # Get search history
    searches = conn.execute('''
        SELECT * FROM asset_searches
        WHERE user_id = ?
        ORDER BY searched_at DESC
        LIMIT 10
    ''', (user_id,)).fetchone()

    conn.close()

    total_unclaimed = sum([a['estimated_value'] for a in assets if a['status'] == 'potential'])

    return render_template('unclaimed_assets.html',
                         assets=[dict(a) for a in assets],
                         total_unclaimed=total_unclaimed)

@app.route('/unclaimed-assets/search', methods=['POST'])
@login_required
def search_unclaimed_assets():
    """Search for unclaimed assets"""
    user_id = session.get('user_id')
    deceased_name = request.form.get('deceased_name')
    deceased_ssn = request.form.get('deceased_ssn')
    states = request.form.getlist('states')

    # This would integrate with actual unclaimed property databases
    # For MVP, we'll simulate some results
    simulated_results = generate_simulated_unclaimed_assets(deceased_name, states)

    conn = get_db()

    # Save search
    conn.execute('''
        INSERT INTO asset_searches (user_id, search_params, results_count, searched_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, json.dumps({'name': deceased_name, 'states': states}),
          len(simulated_results), datetime.now()))

    # Save found assets
    for asset in simulated_results:
        conn.execute('''
            INSERT INTO unclaimed_assets
            (user_id, asset_type, state, holder_name, estimated_value, status, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, asset['type'], asset['state'], asset['holder'],
              asset['value'], 'potential', asset['url']))

    conn.commit()
    conn.close()

    return redirect(url_for('unclaimed_assets'))

# =================== FINANCIAL ADVISOR MATCHING ===================

@app.route('/advisors')
@login_required
def advisor_matching():
    """Financial Advisor Matching Engine"""
    conn = get_db()

    # Get recommended advisors based on user profile
    advisors = conn.execute('''
        SELECT * FROM financial_advisors
        ORDER BY rating DESC
        LIMIT 12
    ''').fetchall()

    conn.close()

    return render_template('advisors.html', advisors=[dict(a) for a in advisors])

@app.route('/advisors/<int:advisor_id>')
@login_required
def advisor_detail(advisor_id):
    """Advisor detail page"""
    conn = get_db()

    advisor = conn.execute('''
        SELECT * FROM financial_advisors WHERE id = ?
    ''', (advisor_id,)).fetchone()

    reviews = conn.execute('''
        SELECT * FROM advisor_reviews WHERE advisor_id = ?
        ORDER BY created_at DESC
    ''', (advisor_id,)).fetchall()

    conn.close()

    return render_template('advisor_detail.html',
                         advisor=dict(advisor),
                         reviews=[dict(r) for r in reviews])

# =================== ESTATE SETTLEMENT CHECKLIST ===================

@app.route('/checklist')
@login_required
def estate_checklist():
    """Estate Settlement Checklist"""
    # For MVP, provide informational static checklist
    # This is educational content to help beneficiaries understand what needs to be done

    tasks_by_category = {
        'Immediate Actions (First 2 Weeks)': [
            {'id': 1, 'title': 'Obtain death certificates', 'description': 'Order 10-15 certified copies - you\'ll need these for banks, insurance, property transfers', 'priority': 'high', 'status': 'pending'},
            {'id': 2, 'title': 'Notify Social Security Administration', 'description': 'Call 1-800-772-1213 to report the death and stop benefit payments', 'priority': 'high', 'status': 'pending'},
            {'id': 3, 'title': 'Contact life insurance companies', 'description': 'File claims for any life insurance policies', 'priority': 'high', 'status': 'pending'},
            {'id': 4, 'title': 'Secure property and assets', 'description': 'Change locks if needed, secure valuables, take inventory', 'priority': 'medium', 'status': 'pending'},
        ],
        'Financial & Legal (First Month)': [
            {'id': 5, 'title': 'Consult with estate attorney', 'description': 'Get professional guidance on probate and estate administration', 'priority': 'high', 'status': 'pending'},
            {'id': 6, 'title': 'Open estate bank account', 'description': 'Set up a dedicated account for managing estate funds', 'priority': 'high', 'status': 'pending'},
            {'id': 7, 'title': 'Locate important documents', 'description': 'Find will, trust documents, account statements, deeds, titles', 'priority': 'high', 'status': 'pending'},
            {'id': 8, 'title': 'Notify creditors and cancel services', 'description': 'Stop credit cards, subscriptions, utilities if property is vacant', 'priority': 'medium', 'status': 'pending'},
        ],
        'Asset Management (First 3 Months)': [
            {'id': 9, 'title': 'Complete asset inventory', 'description': 'Document all bank accounts, investments, real estate, vehicles, personal property', 'priority': 'high', 'status': 'pending'},
            {'id': 10, 'title': 'Get property appraisals', 'description': 'Obtain date-of-death valuations for real estate and valuable items', 'priority': 'medium', 'status': 'pending'},
            {'id': 11, 'title': 'Transfer retirement accounts', 'description': 'Complete beneficiary claim forms for IRAs, 401(k)s, pensions', 'priority': 'high', 'status': 'pending'},
            {'id': 12, 'title': 'Transfer vehicle titles', 'description': 'Update ownership at DMV for cars, boats, RVs', 'priority': 'medium', 'status': 'pending'},
        ],
        'Tax Compliance (Within 9-12 Months)': [
            {'id': 13, 'title': 'File final income tax return', 'description': 'Prepare Form 1040 for January 1 through date of death', 'priority': 'high', 'status': 'pending'},
            {'id': 14, 'title': 'Determine if estate tax applies', 'description': 'Estate tax only applies if estate exceeds $13.61M (2024)', 'priority': 'medium', 'status': 'pending'},
            {'id': 15, 'title': 'File state estate tax if required', 'description': 'Some states have lower thresholds than federal', 'priority': 'medium', 'status': 'pending'},
            {'id': 16, 'title': 'Obtain tax clearance letters', 'description': 'Get confirmation of no outstanding tax liabilities', 'priority': 'medium', 'status': 'pending'},
        ],
        'Final Distributions (6-12 Months)': [
            {'id': 17, 'title': 'Pay outstanding debts', 'description': 'Settle legitimate creditor claims from estate funds', 'priority': 'high', 'status': 'pending'},
            {'id': 18, 'title': 'Distribute specific bequests', 'description': 'Give items left to specific people per the will', 'priority': 'medium', 'status': 'pending'},
            {'id': 19, 'title': 'Distribute financial assets', 'description': 'Transfer cash, securities, and remaining assets to heirs', 'priority': 'high', 'status': 'pending'},
            {'id': 20, 'title': 'File final accounting', 'description': 'Document all estate transactions and close estate', 'priority': 'medium', 'status': 'pending'},
        ]
    }

    # Calculate totals
    total_tasks = sum(len(tasks) for tasks in tasks_by_category.values())
    completed_tasks = 0
    progress = 0

    return render_template('checklist.html',
                         tasks_by_category=tasks_by_category,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         progress=progress)

@app.route('/checklist/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark task as complete"""
    conn = get_db()

    conn.execute('''
        UPDATE estate_tasks
        SET status = 'completed', completed_at = ?
        WHERE id = ?
    ''', (datetime.now(), task_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

# =================== TAX PLANNING ===================

@app.route('/tax-planning')
@login_required
def tax_planning():
    """Tax Planning and Guidance"""
    conn = get_db()
    user_email = session.get('user_email')

    # Get user's cases to calculate inheritance
    cases = conn.execute('''
        SELECT account_type, account_balance, financial_institution
        FROM cases
        WHERE beneficiary_email = ?
    ''', (user_email,)).fetchall()

    # Calculate estimated taxes (simplified for demo)
    total_inheritance = sum([c['account_balance'] for c in cases])

    # Estimate federal withholding (10% for IRAs, 20% for 401k)
    total_federal_tax = 0
    total_state_tax = 0
    tax_data = []

    for case in cases:
        if case['account_type'] in ['401K', '401(k)']:
            fed_rate = 0.20
        else:
            fed_rate = 0.10

        state_rate = 0.093  # California rate as example

        fed_tax = case['account_balance'] * fed_rate
        state_tax = case['account_balance'] * state_rate

        total_federal_tax += fed_tax
        total_state_tax += state_tax

        tax_data.append({
            'institution_name': case['financial_institution'],
            'account_type': case['account_type'],
            'distribution_amount': case['account_balance'],
            'federal_withholding': fed_tax,
            'state_withholding': state_tax,
            'net_distribution': case['account_balance'] - fed_tax - state_tax
        })

    total_net = total_inheritance - total_federal_tax - total_state_tax

    # Get tax planning tips
    tips = get_tax_planning_tips(total_inheritance, tax_data)

    conn.close()

    return render_template('tax_planning.html',
                         tax_data=tax_data,
                         total_inheritance=total_inheritance,
                         total_federal_tax=total_federal_tax,
                         total_state_tax=total_state_tax,
                         total_net=total_net,
                         tips=tips)

# =================== GRIEF RESOURCES ===================

@app.route('/grief-resources')
@login_required
def grief_resources():
    """Grief Resources and Support"""
    conn = get_db()

    # Get grief resources
    resources = conn.execute('''
        SELECT * FROM grief_resources
        ORDER BY category, title
    ''').fetchall()

    # Group by category
    resources_by_category = {}
    for resource in resources:
        category = resource['category']
        if category not in resources_by_category:
            resources_by_category[category] = []
        resources_by_category[category].append(dict(resource))

    conn.close()

    return render_template('grief_resources.html',
                         resources_by_category=resources_by_category)

# =================== HELPER FUNCTIONS ===================

def generate_simulated_unclaimed_assets(deceased_name, states):
    """Generate simulated unclaimed assets for demonstration"""
    asset_types = [
        {'type': 'Bank Account', 'holder': 'Wells Fargo', 'value': 2500.00},
        {'type': 'Utility Refund', 'holder': 'PG&E', 'value': 150.00},
        {'type': 'Insurance Policy', 'holder': 'State Farm', 'value': 5000.00},
        {'type': 'Stock Certificate', 'holder': 'Charles Schwab', 'value': 3200.00},
        {'type': 'Pension Fund', 'holder': 'CalPERS', 'value': 12000.00},
    ]

    results = []
    for state in states:
        for i, asset in enumerate(asset_types[:3]):  # Return 3 per state
            results.append({
                'type': asset['type'],
                'state': state,
                'holder': asset['holder'],
                'value': asset['value'],
                'url': f'https://www.unclaimed.org/{state.lower()}'
            })

    return results

def get_tax_planning_tips(total_inheritance, tax_data):
    """Generate personalized tax planning tips"""
    tips = []

    if total_inheritance > 100000:
        tips.append({
            'title': 'Consider a Tax Professional',
            'description': 'With an inheritance over $100,000, consulting a CPA or tax attorney can help minimize your tax burden.',
            'priority': 'high'
        })

    # Check for IRA accounts
    has_ira = any(t['account_type'] == 'IRA' for t in tax_data)
    if has_ira:
        tips.append({
            'title': 'IRA Distribution Strategy',
            'description': 'Consider the 10-year rule for inherited IRAs. Spreading distributions can help minimize tax bracket impact.',
            'priority': 'high'
        })

    tips.append({
        'title': 'Track All Tax Documents',
        'description': 'Keep all 1099-R forms and tax withholding receipts for your tax return.',
        'priority': 'medium'
    })

    tips.append({
        'title': 'Estimated Tax Payments',
        'description': 'If withholding is insufficient, consider quarterly estimated tax payments to avoid penalties.',
        'priority': 'medium'
    })

    return tips

# =================== INITIALIZATION ===================

def init_executour_tables():
    """Initialize Executour-specific database tables"""
    conn = get_db()
    cursor = conn.cursor()

    # Unclaimed assets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unclaimed_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL,
            state TEXT,
            holder_name TEXT,
            estimated_value REAL,
            status TEXT DEFAULT 'potential',
            source_url TEXT,
            claim_initiated_at TIMESTAMP,
            claimed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Asset searches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asset_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_params TEXT,
            results_count INTEGER,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Financial advisors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_advisors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            firm_name TEXT,
            specialties TEXT,
            location TEXT,
            rating REAL,
            aum REAL,
            min_investment REAL,
            fee_structure TEXT,
            certifications TEXT,
            bio TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Advisor reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advisor_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_id INTEGER NOT NULL,
            user_id INTEGER,
            rating INTEGER,
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (advisor_id) REFERENCES financial_advisors(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Estate tasks/checklist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estate_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            due_date DATE,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Grief resources table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grief_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            resource_type TEXT,
            url TEXT,
            phone TEXT,
            email TEXT,
            cost TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_executour_tables()
    print("=" * 60)
    print("🏛️  EXECUTOUR - Unified Inheritance Platform")
    print("=" * 60)
    print("Server running at: http://localhost:5006")
    print("=" * 60)
    app.run(debug=True, port=5006, host='0.0.0.0')
