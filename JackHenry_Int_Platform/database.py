#!/usr/bin/env python3
"""
Jack Henry Integration Platform - Database Schema
Stores customer, account, and beneficiary data from Jack Henry APIs
"""

import sqlite3
from datetime import datetime
import json

DATABASE_PATH = 'jackhenry_data.db'

def init_database():
    """Initialize the Jack Henry integration database"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    # Customers Table (from OpenID Connect identity token claims)
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            sub TEXT UNIQUE NOT NULL,
            given_name TEXT,
            family_name TEXT,
            full_name TEXT,
            email TEXT,
            email_verified INTEGER DEFAULT 0,
            phone_number TEXT,
            phone_number_verified INTEGER DEFAULT 0,
            birthdate TEXT,
            address_json TEXT,
            ssn TEXT,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL
        )
    ''')

    # Accounts Table (from Consumer API /users/{user_id}/accounts)
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            customer_sub TEXT NOT NULL,
            account_uuid TEXT,
            account_number TEXT,
            account_type TEXT,
            account_name TEXT,
            status TEXT DEFAULT 'active',
            balance_available REAL,
            balance_current REAL,
            balance_pending REAL,
            currency TEXT DEFAULT 'USD',
            opened_date TEXT,
            closed_date TEXT,
            is_primary INTEGER DEFAULT 0,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL,
            fetched_date TEXT,
            FOREIGN KEY (customer_sub) REFERENCES customers(sub)
        )
    ''')

    # Beneficiaries Table (from jXchange SOAP API)
    c.execute('''
        CREATE TABLE IF NOT EXISTS beneficiaries (
            beneficiary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            beneficiary_type TEXT NOT NULL,
            designation_type TEXT,
            full_name TEXT NOT NULL,
            first_name TEXT,
            middle_name TEXT,
            last_name TEXT,
            suffix TEXT,
            relationship TEXT,
            ssn TEXT,
            tax_id TEXT,
            date_of_birth TEXT,
            address_json TEXT,
            phone TEXT,
            email TEXT,
            percentage REAL,
            is_primary INTEGER DEFAULT 1,
            is_contingent INTEGER DEFAULT 0,
            share_type TEXT,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )
    ''')

    # Transactions Table (from Consumer API /accounts/{account_id}/transactions)
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            transaction_uuid TEXT,
            transaction_date TEXT NOT NULL,
            posted_date TEXT,
            amount REAL NOT NULL,
            description TEXT,
            transaction_type TEXT,
            category TEXT,
            merchant_name TEXT,
            status TEXT DEFAULT 'posted',
            balance_after REAL,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )
    ''')

    # API Sync Log (track synchronization history)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sync_log (
            sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            sync_date TEXT NOT NULL,
            customer_sub TEXT,
            records_fetched INTEGER DEFAULT 0,
            records_created INTEGER DEFAULT 0,
            records_updated INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success',
            error_message TEXT,
            api_endpoint TEXT,
            execution_time_ms INTEGER
        )
    ''')

    # OAuth Tokens Table (store access/refresh tokens)
    c.execute('''
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            token_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_sub TEXT UNIQUE,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            id_token TEXT,
            token_type TEXT DEFAULT 'Bearer',
            expires_at TEXT,
            scope TEXT,
            created_date TEXT NOT NULL,
            last_refreshed TEXT
        )
    ''')

    # API Configuration Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_config (
            config_key TEXT PRIMARY KEY,
            config_value TEXT NOT NULL,
            description TEXT,
            last_updated TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("Jack Henry database initialized successfully")

def seed_api_config():
    """Seed initial API configuration"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    now = datetime.utcnow().isoformat()

    configs = [
        {
            'key': 'auth_base_url',
            'value': 'https://digital.garden-fi.com',
            'description': 'Jack Henry Garden OAuth base URL'
        },
        {
            'key': 'api_base_url',
            'value': 'https://api.digital.garden-fi.com',
            'description': 'Jack Henry Consumer API base URL'
        },
        {
            'key': 'client_id',
            'value': 'YOUR_CLIENT_ID',
            'description': 'OAuth Client ID (replace with actual)'
        },
        {
            'key': 'client_secret',
            'value': 'YOUR_CLIENT_SECRET',
            'description': 'OAuth Client Secret (replace with actual)'
        },
        {
            'key': 'redirect_uri',
            'value': 'http://localhost:5012/callback',
            'description': 'OAuth redirect URI'
        },
        {
            'key': 'scope',
            'value': 'openid profile email phone address offline_access banno',
            'description': 'OAuth requested scopes'
        },
        {
            'key': 'jxchange_endpoint',
            'value': 'https://api.garden-fi.com/jxchange',
            'description': 'jXchange SOAP API endpoint (if available)'
        }
    ]

    for config in configs:
        c.execute('''
            INSERT OR REPLACE INTO api_config (config_key, config_value, description, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (config['key'], config['value'], config['description'], now))

    conn.commit()
    conn.close()
    print(f"Seeded {len(configs)} API configuration entries")

def get_config(key):
    """Get configuration value"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('SELECT config_value FROM api_config WHERE config_key = ?', (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_config(key, value):
    """Update configuration value"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute('''
        UPDATE api_config
        SET config_value = ?, last_updated = ?
        WHERE config_key = ?
    ''', (value, now, key))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_database()
    seed_api_config()
