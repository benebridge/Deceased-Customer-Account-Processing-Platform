#!/usr/bin/env python3
"""
Jack Henry API Client
Handles OAuth authentication and API calls to Jack Henry Garden environment
"""

import requests
import sqlite3
from datetime import datetime, timedelta
import json
import base64
import secrets
import hashlib
from urllib.parse import urlencode, parse_qs, urlparse
from database import DATABASE_PATH, get_config, update_config

class JackHenryClient:
    """Client for Jack Henry Consumer API and OAuth"""

    def __init__(self):
        self.auth_base_url = get_config('auth_base_url')
        self.api_base_url = get_config('api_base_url')
        self.client_id = get_config('client_id')
        self.client_secret = get_config('client_secret')
        self.redirect_uri = get_config('redirect_uri')
        self.scope = get_config('scope')

    def generate_pkce_pair(self):
        """
        Generate PKCE code_verifier and code_challenge
        Returns: (code_verifier, code_challenge)
        """
        # Generate code_verifier (43-128 characters, URL-safe)
        code_verifier = secrets.token_urlsafe(64)

        # Generate code_challenge (SHA256 hash of verifier, base64-url-encoded)
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def generate_authorization_url(self, state=None):
        """
        Generate OAuth 2.0 authorization URL for user login with PKCE
        Returns: (authorization_url, state, code_verifier)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        # Generate PKCE parameters
        code_verifier, code_challenge = self.generate_pkce_pair()

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

        auth_url = f"{self.auth_base_url}/oidc/auth?{urlencode(params)}"

        # Debug logging
        print(f"\n=== OAuth Authorization URL Debug ===")
        print(f"Auth Base URL: {self.auth_base_url}")
        print(f"Client ID: {self.client_id}")
        print(f"Redirect URI: {self.redirect_uri}")
        print(f"Scope: {self.scope}")
        print(f"State: {state}")
        print(f"Code Challenge: {code_challenge}")
        print(f"Full URL: {auth_url}")
        print(f"=====================================\n")

        return auth_url, state, code_verifier

    def exchange_code_for_tokens(self, authorization_code, code_verifier):
        """
        Exchange authorization code for access token
        Returns: dict with access_token, refresh_token, id_token, expires_in, scope
        """
        token_url = f"{self.auth_base_url}/oidc/token"

        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code_verifier': code_verifier
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()
        return token_data

    def refresh_access_token(self, refresh_token):
        """
        Refresh an expired access token
        Returns: dict with new access_token and other token info
        """
        token_url = f"{self.auth_base_url}/oidc/token"

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        return response.json()

    def decode_id_token(self, id_token):
        """
        Decode JWT ID token to extract user claims
        Note: This is a basic decoder - in production use proper JWT library with signature verification
        """
        try:
            # Split JWT into parts
            parts = id_token.split('.')
            if len(parts) != 3:
                return None

            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding

            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            return claims
        except Exception as e:
            print(f"Error decoding ID token: {e}")
            return None

    def save_tokens(self, customer_sub, token_data):
        """Save OAuth tokens to database"""
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()

        now = datetime.utcnow().isoformat()
        expires_in = token_data.get('expires_in', 3600)
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        c.execute('''
            INSERT OR REPLACE INTO oauth_tokens
            (customer_sub, access_token, refresh_token, id_token, token_type, expires_at, scope, created_date, last_refreshed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_sub,
            token_data.get('access_token'),
            token_data.get('refresh_token'),
            token_data.get('id_token'),
            token_data.get('token_type', 'Bearer'),
            expires_at,
            token_data.get('scope'),
            now,
            now
        ))

        conn.commit()
        conn.close()

    def get_access_token(self, customer_sub):
        """Get valid access token for customer, refreshing if needed"""
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()

        c.execute('''
            SELECT access_token, refresh_token, expires_at
            FROM oauth_tokens
            WHERE customer_sub = ?
        ''', (customer_sub,))

        result = c.fetchone()
        conn.close()

        if not result:
            return None

        access_token, refresh_token, expires_at = result

        # Check if token is expired
        if datetime.fromisoformat(expires_at) <= datetime.utcnow():
            # Refresh the token
            if refresh_token:
                try:
                    new_token_data = self.refresh_access_token(refresh_token)
                    self.save_tokens(customer_sub, new_token_data)
                    return new_token_data.get('access_token')
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    return None
            else:
                return None

        return access_token

    def get_user_accounts(self, customer_sub):
        """
        Get all accounts for a user from Consumer API
        GET /users/{user_id}/accounts
        """
        access_token = self.get_access_token(customer_sub)
        if not access_token:
            raise Exception("No valid access token available")

        url = f"{self.api_base_url}/users/{customer_sub}/accounts"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_account_transactions(self, customer_sub, account_id, limit=100):
        """
        Get transactions for an account from Consumer API
        GET /users/{user_id}/accounts/{account_id}/transactions
        """
        access_token = self.get_access_token(customer_sub)
        if not access_token:
            raise Exception("No valid access token available")

        url = f"{self.api_base_url}/users/{customer_sub}/accounts/{account_id}/transactions"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        params = {'limit': limit}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.json()

    def save_customer_from_token(self, token_data):
        """Extract customer info from ID token and save to database"""
        id_token = token_data.get('id_token')
        if not id_token:
            return None

        claims = self.decode_id_token(id_token)
        if not claims:
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()

        now = datetime.utcnow().isoformat()
        sub = claims.get('sub')

        # Extract address if present
        address_json = None
        if 'address' in claims:
            address_json = json.dumps(claims['address'])

        # Generate customer_id (could use sub or generate UUID)
        customer_id = sub

        c.execute('''
            INSERT OR REPLACE INTO customers
            (customer_id, sub, given_name, family_name, full_name, email, email_verified,
             phone_number, phone_number_verified, birthdate, address_json, created_date, last_updated, last_synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_id,
            sub,
            claims.get('given_name'),
            claims.get('family_name'),
            claims.get('name'),
            claims.get('email'),
            1 if claims.get('email_verified') else 0,
            claims.get('phone_number'),
            1 if claims.get('phone_number_verified') else 0,
            claims.get('birthdate'),
            address_json,
            now,
            now,
            now
        ))

        conn.commit()
        conn.close()

        return customer_id

    def sync_customer_accounts(self, customer_sub):
        """Sync all accounts for a customer to database"""
        try:
            start_time = datetime.utcnow()
            accounts_data = self.get_user_accounts(customer_sub)

            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()

            now = datetime.utcnow().isoformat()
            records_created = 0
            records_updated = 0

            # Process accounts array
            accounts = accounts_data if isinstance(accounts_data, list) else accounts_data.get('accounts', [])

            for account in accounts:
                account_id = account.get('id')

                # Check if account exists
                c.execute('SELECT account_id FROM accounts WHERE account_id = ?', (account_id,))
                exists = c.fetchone()

                if exists:
                    records_updated += 1
                else:
                    records_created += 1

                c.execute('''
                    INSERT OR REPLACE INTO accounts
                    (account_id, customer_sub, account_uuid, account_type, status,
                     created_date, last_updated, last_synced, fetched_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account_id,
                    customer_sub,
                    account.get('id'),
                    account.get('type', 'UNKNOWN'),
                    'active',
                    now if not exists else exists[0],
                    now,
                    now,
                    account.get('fetchedDate')
                ))

            conn.commit()

            # Log sync
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            c.execute('''
                INSERT INTO sync_log
                (sync_type, sync_date, customer_sub, records_fetched, records_created, records_updated,
                 status, api_endpoint, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'accounts',
                now,
                customer_sub,
                len(accounts),
                records_created,
                records_updated,
                'success',
                '/users/{user_id}/accounts',
                execution_time
            ))

            conn.commit()
            conn.close()

            return {'success': True, 'accounts': len(accounts), 'created': records_created, 'updated': records_updated}

        except Exception as e:
            print(f"Error syncing accounts: {e}")
            return {'success': False, 'error': str(e)}


class JXChangeClient:
    """Client for Jack Henry jXchange SOAP API (beneficiary data)"""

    def __init__(self):
        self.endpoint = get_config('jxchange_endpoint')
        # Note: jXchange typically uses different auth - may need institution credentials

    def get_account_beneficiaries(self, account_number):
        """
        Get beneficiaries for an account using jXchange AcctInq service
        This is a placeholder - actual implementation requires SOAP XML construction
        """
        # TODO: Implement SOAP request for AcctInq
        # This would use the AcctInq service to retrieve account details including beneficiaries
        pass

    def sync_account_beneficiaries(self, account_id, account_number):
        """
        Sync beneficiary data for an account to database
        This is a placeholder for when jXchange access is available
        """
        # TODO: Implement beneficiary sync from jXchange
        # Would call get_account_beneficiaries and save to database
        pass
