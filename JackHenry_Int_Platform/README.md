# Jack Henry Integration Platform

A platform for integrating with Jack Henry's Garden test environment APIs to sync customer, account, and beneficiary data.

## Overview

This platform connects to Jack Henry's Developer APIs (https://jackhenry.dev) to retrieve and store banking data in a local database. It's designed to work with the Garden test environment for development and testing purposes.

## Features

- **OAuth 2.0 + OpenID Connect Authentication** - Secure user authentication via Jack Henry's Garden environment
- **Consumer API Integration** - Retrieves account and transaction data
- **jXchange API Integration** - Placeholder for beneficiary data retrieval (SOAP API)
- **Local Database Storage** - SQLite database stores all synced data
- **Web Interface** - View customers, accounts, and beneficiaries through a clean web UI
- **JSON Export** - Export all data as JSON for use in other platforms
- **Sync Logging** - Track all API synchronization activities

## Running on

**http://localhost:5012**

## Database Schema

The platform creates a SQLite database (`jackhenry_data.db`) with the following tables:

- **customers** - Customer profile information from OpenID Connect claims
- **accounts** - Account data from Consumer API
- **beneficiaries** - Beneficiary designations (from jXchange)
- **transactions** - Account transactions
- **oauth_tokens** - OAuth access/refresh tokens
- **sync_log** - API synchronization history
- **api_config** - API configuration settings

## Setup Instructions

### 1. Obtain Jack Henry API Credentials

1. Go to https://jackhenry.dev
2. Create a developer account
3. Generate test credentials (client_id and client_secret)
4. Configure your redirect URI: `http://localhost:5012/callback`

### 2. Configure the Platform

1. Navigate to http://localhost:5012/config
2. Enter your API credentials:
   - **Client ID** - From Jack Henry developer dashboard
   - **Client Secret** - From Jack Henry developer dashboard
   - **Auth Base URL** - Default: `https://digital.garden-fi.com`
   - **API Base URL** - Default: `https://api.digital.garden-fi.com`
   - **Redirect URI** - Default: `http://localhost:5012/callback`
   - **Scope** - Default: `openid profile email phone address offline_access banno`

### 3. Authenticate and Sync Data

1. Click "Authenticate & Sync New Customer" on the dashboard
2. Log in with your Garden test user credentials
3. The platform will automatically:
   - Exchange authorization code for tokens
   - Extract customer information from ID token
   - Sync account data from Consumer API
   - Store everything in the local database

## API Endpoints

### Web Pages
- `/` - Dashboard
- `/customers` - Customer list
- `/customer/<customer_id>` - Customer detail
- `/accounts` - Account list
- `/beneficiaries` - Beneficiary list
- `/config` - API configuration

### API Endpoints
- `/auth/login` - Initiate OAuth flow
- `/callback` - OAuth callback handler
- `/sync/<customer_sub>` - Manual sync trigger
- `/export/customers` - Export customers as JSON
- `/export/accounts` - Export accounts as JSON
- `/export/beneficiaries` - Export beneficiaries as JSON
- `/export/all` - Export complete database as JSON

## Data Export

You can export all synced data as JSON:

```bash
curl http://localhost:5012/export/all > jackhenry_data.json
```

This exports:
- All customers with profile information
- All accounts with details
- All beneficiaries with designations
- All transactions
- Sync log history

## Architecture

### Files

- **app.py** - Flask application (main web server)
- **database.py** - Database schema and initialization
- **jackhenry_client.py** - Jack Henry API client library
  - `JackHenryClient` - Consumer API and OAuth
  - `JXChangeClient` - jXchange SOAP API (placeholder)
- **templates/** - HTML templates for web interface
  - dashboard.html
  - customers.html
  - customer_detail.html
  - accounts.html
  - beneficiaries.html
  - config.html

### API Integration

**Consumer API (REST)**
- OAuth 2.0 Bearer token authentication
- Endpoints used:
  - `GET /users/{user_id}/accounts` - Retrieve accounts
  - `GET /users/{user_id}/accounts/{account_id}/transactions` - Retrieve transactions

**jXchange API (SOAP)** - Placeholder
- Services identified:
  - AcctBenfAdd - Add beneficiaries
  - AcctInq - Account inquiry with beneficiaries
  - TaxPlanBenfAddValidate - Retirement account beneficiaries

## Next Steps

After syncing data from Jack Henry APIs, you can:

1. **Export the data** - Use `/export/all` to get JSON data
2. **Create matching documents** - Use the customer/beneficiary data to generate:
   - Death certificates matching customer profiles
   - IDs matching beneficiary information
   - Claim forms with correct account details
3. **Test claim processing** - Use the synced data in your death claim workflow

## Notes

- This platform is designed for the **Garden test environment** only
- Beneficiary data requires jXchange SOAP API access (not implemented yet)
- The database is local SQLite - data persists between restarts
- OAuth tokens are automatically refreshed when expired
- All dates/times are stored in UTC ISO format

## Security Considerations

- Client secret is stored in plaintext in the database (use environment variables in production)
- OAuth tokens are stored in the database (use secure storage in production)
- This is a development/test platform - not production-ready
- HTTPS is required for redirect URIs except localhost

## Troubleshooting

**"API Not Configured" warning**
- Go to /config and enter your Jack Henry API credentials

**Authentication fails**
- Verify client_id and client_secret are correct
- Check that redirect_uri matches exactly: `http://localhost:5012/callback`
- Ensure Garden test user is enrolled

**No accounts synced**
- Check sync_log table for errors
- Verify OAuth token is valid
- Test API access directly with your credentials

**Beneficiary data not appearing**
- jXchange integration is not yet implemented
- Requires SOAP API access and additional credentials
- Placeholder code is in jackhenry_client.py
