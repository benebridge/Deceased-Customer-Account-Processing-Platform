"""
Seed data for Executour platform
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = '../benebridge.db'

def seed_all():
    """Seed all Executour data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Seed Financial Advisors
    advisors = [
        {
            'name': 'Sarah Mitchell, CFP',
            'firm_name': 'Heritage Wealth Management',
            'specialties': 'Estate Planning, Inherited IRAs, Tax-Efficient Investing',
            'location': 'San Francisco, CA',
            'rating': 4.8,
            'aum': 250,
            'min_investment': 250000,
            'fee_structure': '1% AUM',
            'certifications': 'CFP, CPA, ChFC',
            'bio': 'Sarah has over 15 years of experience helping clients navigate complex estate and inheritance situations. She specializes in tax-efficient distribution strategies for inherited retirement accounts.',
            'phone': '(415) 555-0123',
            'email': '[email protected]',
            'website': 'https://heritagewm.example.com'
        },
        {
            'name': 'Michael Chen, CFA',
            'firm_name': 'Pacific Coast Advisors',
            'specialties': 'Wealth Management, Beneficiary Planning, Multi-Generational Wealth',
            'location': 'Los Angeles, CA',
            'rating': 4.9,
            'aum': 500,
            'min_investment': 500000,
            'fee_structure': '0.85% AUM',
            'certifications': 'CFA, CFP, CIMA',
            'bio': 'Michael specializes in helping families manage inherited wealth across generations. His comprehensive approach integrates tax planning, investment management, and estate planning.',
            'phone': '(310) 555-0456',
            'email': '[email protected]',
            'website': 'https://pacificcoast.example.com'
        },
        {
            'name': 'Jennifer Rodriguez, EA',
            'firm_name': 'TaxWise Financial Planning',
            'specialties': 'Tax Planning, IRS Representation, Inherited Asset Management',
            'location': 'San Diego, CA',
            'rating': 4.7,
            'aum': 150,
            'min_investment': 100000,
            'fee_structure': 'Hourly + 0.75% AUM',
            'certifications': 'EA, CFP, CTFA',
            'bio': 'Jennifer combines tax expertise with financial planning to help beneficiaries minimize tax impact on inheritances. She has successfully represented clients before the IRS in complex estate matters.',
            'phone': '(619) 555-0789',
            'email': '[email protected]',
            'website': 'https://taxwisefp.example.com'
        },
        {
            'name': 'David Thompson, JD',
            'firm_name': 'Thompson Estate & Financial Services',
            'specialties': 'Estate Law, Trust Administration, Beneficiary Rights',
            'location': 'Sacramento, CA',
            'rating': 4.6,
            'aum': 200,
            'min_investment': 150000,
            'fee_structure': 'Flat Fee + 1% AUM',
            'certifications': 'JD, CFP, CLU',
            'bio': 'As both an attorney and financial advisor, David provides unique insight into the legal and financial aspects of inheritance. He helps beneficiaries understand their rights and optimize their financial outcomes.',
            'phone': '(916) 555-0234',
            'email': '[email protected]',
            'website': 'https://thompsonefs.example.com'
        }
    ]

    for advisor in advisors:
        cursor.execute('''
            INSERT INTO financial_advisors
            (name, firm_name, specialties, location, rating, aum, min_investment,
             fee_structure, certifications, bio, phone, email, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            advisor['name'], advisor['firm_name'], advisor['specialties'],
            advisor['location'], advisor['rating'], advisor['aum'],
            advisor['min_investment'], advisor['fee_structure'],
            advisor['certifications'], advisor['bio'], advisor['phone'],
            advisor['email'], advisor['website']
        ))

    # Seed Estate Tasks for user_id = 1
    tasks = [
        # Immediate Actions
        ('Immediate Actions', 'Obtain death certificates', 'Order 10-15 certified copies for various institutions', 'high', 'pending', (datetime.now() + timedelta(days=3)).date()),
        ('Immediate Actions', 'Notify Social Security Administration', 'Report death to prevent benefit overpayment', 'high', 'pending', (datetime.now() + timedelta(days=7)).date()),
        ('Immediate Actions', 'Contact life insurance companies', 'File claims for any life insurance policies', 'high', 'pending', (datetime.now() + timedelta(days=14)).date()),
        ('Immediate Actions', 'Secure property and assets', 'Change locks, secure valuables, inventory belongings', 'medium', 'completed', None),

        # Financial & Legal
        ('Financial & Legal', 'Open estate bank account', 'Set up account for managing estate funds', 'high', 'pending', (datetime.now() + timedelta(days=30)).date()),
        ('Financial & Legal', 'File for probate (if required)', 'Consult attorney about probate requirements', 'high', 'pending', (datetime.now() + timedelta(days=45)).date()),
        ('Financial & Legal', 'Obtain EIN for estate', 'Get tax ID number from IRS for estate', 'medium', 'pending', (datetime.now() + timedelta(days=30)).date()),
        ('Financial & Legal', 'Review and update will', 'Understand provisions and beneficiary designations', 'high', 'completed', None),

        # Asset Management
        ('Asset Management', 'Inventory all assets', 'Create comprehensive list of all assets and accounts', 'high', 'completed', None),
        ('Asset Management', 'Get property appraisals', 'Obtain valuations for real estate and valuable items', 'medium', 'pending', (datetime.now() + timedelta(days=60)).date()),
        ('Asset Management', 'Transfer vehicle titles', 'Update ownership for cars, boats, etc.', 'medium', 'pending', (datetime.now() + timedelta(days=90)).date()),
        ('Asset Management', 'Cancel subscriptions and services', 'Stop recurring charges and memberships', 'low', 'pending', (datetime.now() + timedelta(days=30)).date()),

        # Tax & Compliance
        ('Tax & Compliance', 'File final income tax return', 'Prepare and file deceased\'s final 1040', 'high', 'pending', (datetime.now() + timedelta(days=120)).date()),
        ('Tax & Compliance', 'File estate tax return (if required)', 'Form 706 if estate exceeds threshold', 'high', 'pending', (datetime.now() + timedelta(days=270)).date()),
        ('Tax & Compliance', 'Obtain tax clearance', 'Get confirmation of no outstanding tax liabilities', 'medium', 'pending', (datetime.now() + timedelta(days=180)).date()),

        # Distributions
        ('Distributions', 'Pay outstanding debts', 'Settle credit cards, loans, and other liabilities', 'high', 'pending', (datetime.now() + timedelta(days=90)).date()),
        ('Distributions', 'Distribute personal property', 'Allocate items to beneficiaries per will', 'medium', 'pending', (datetime.now() + timedelta(days=120)).date()),
        ('Distributions', 'Distribute financial assets', 'Transfer cash, securities, and accounts', 'high', 'pending', (datetime.now() + timedelta(days=180)).date()),
        ('Distributions', 'Close estate accounts', 'Final accounting and close estate bank account', 'medium', 'pending', (datetime.now() + timedelta(days=365)).date()),
    ]

    for category, title, description, priority, status, due_date in tasks:
        cursor.execute('''
            INSERT INTO estate_tasks
            (user_id, category, title, description, priority, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (1, category, title, description, priority, status, due_date))

    # Seed Grief Resources
    resources = [
        # Professional Counseling
        ('Professional Counseling', 'GriefShare Support Groups', 'Faith-based grief support groups meeting weekly across the country', 'Support Group', 'https://www.griefshare.org', '(800) 395-5755', None, 'Free'),
        ('Professional Counseling', 'The Grief Recovery Method', 'Evidence-based grief recovery program with certified specialists', 'Counseling', 'https://www.griefrecoverymethod.com', '(818) 907-9600', '[email protected]', 'Varies'),
        ('Professional Counseling', 'BetterHelp Online Therapy', 'Professional online counseling with licensed therapists', 'Online Resource', 'https://www.betterhelp.com', None, None, '$60-90/week'),

        # Support Groups
        ('Support Groups', 'The Compassionate Friends', 'Support for families after the death of a child', 'Support Group', 'https://www.compassionatefriends.org', '(877) 969-0010', '[email protected]', 'Free'),
        ('Support Groups', 'AARP Grief and Loss Programs', 'Free online and in-person grief support for all ages', 'Support Group', 'https://www.aarp.org/grieving', '(888) 687-2277', None, 'Free'),
        ('Support Groups', 'Modern Loss', 'Online community for people experiencing grief', 'Online Resource', 'https://modernloss.com', None, None, 'Free'),

        # Crisis Support
        ('Crisis Support', '988 Suicide & Crisis Lifeline', '24/7 emotional support for people in crisis', 'Hotline', 'https://988lifeline.org', '988', None, 'Free'),
        ('Crisis Support', 'Crisis Text Line', 'Free 24/7 crisis support via text message', 'Hotline', 'https://www.crisistextline.org', 'Text HOME to 741741', None, 'Free'),
        ('Crisis Support', 'SAMHSA National Helpline', 'Treatment referral and information service', 'Hotline', 'https://www.samhsa.gov/find-help/national-helpline', '(800) 662-4357', None, 'Free'),

        # Educational Resources
        ('Educational Resources', 'What\'s Your Grief', 'Articles, podcasts, and courses about grief', 'Online Resource', 'https://whatsyourgrief.com', None, None, 'Free & Paid'),
        ('Educational Resources', 'The Dinner Party', 'Community for 20s and 30s grieving significant loss', 'Online Resource', 'https://thedinnerparty.org', None, '[email protected]', 'Free'),
        ('Educational Resources', 'Center for Loss & Life Transition', 'Resources and training on grief counseling', 'Online Resource', 'https://www.centerforloss.com', '(970) 226-6050', None, 'Free & Paid'),

        # Books & Media
        ('Books & Media', 'Option B by Sheryl Sandberg', 'Building resilience after loss and adversity', 'Book', None, None, None, '$15-20'),
        ('Books & Media', 'The Year of Magical Thinking by Joan Didion', 'Personal memoir about grief after loss of spouse', 'Book', None, None, None, '$15-20'),
        ('Books & Media', 'It\'s OK That You\'re Not OK by Megan Devine', 'Honest approach to grief that defies conventional wisdom', 'Book', None, None, None, '$15-20'),
    ]

    for category, title, description, resource_type, url, phone, email, cost in resources:
        cursor.execute('''
            INSERT INTO grief_resources
            (category, title, description, resource_type, url, phone, email, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (category, title, description, resource_type, url, phone, email, cost))

    conn.commit()
    conn.close()

    print("✓ Executour sample data seeded successfully!")

if __name__ == '__main__':
    seed_all()
