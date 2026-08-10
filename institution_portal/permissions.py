"""
Role-Based Access Control (RBAC) System
Defines permissions for different user roles in the institution portal.
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, request

# =================== ROLE DEFINITIONS ===================

ROLES = {
    'admin': {
        'name': 'Administrator',
        'description': 'Full system access, user management, system configuration',
        'level': 4  # Highest access level
    },
    'manager': {
        'name': 'Manager',
        'description': 'Approve high-value claims, override decisions, view all cases',
        'level': 3
    },
    'compliance': {
        'name': 'Compliance Officer',
        'description': 'Compliance review, regulatory reporting, audit access',
        'level': 2
    },
    'operations': {
        'name': 'Operations Specialist',
        'description': 'Process cases, upload documents, basic workflow tasks',
        'level': 1  # Basic access level
    }
}

# =================== PERMISSION MATRIX ===================

PERMISSIONS = {
    # Case Management
    'view_all_cases': ['admin', 'manager', 'compliance'],
    'view_assigned_cases': ['operations'],
    'create_case': ['admin', 'manager', 'operations'],
    'edit_case': ['admin', 'manager', 'operations'],
    'delete_case': ['admin'],

    # Workflow
    'complete_workflow_task': ['admin', 'manager', 'operations'],
    'override_workflow': ['admin', 'manager'],
    'reassign_case': ['admin', 'manager'],

    # Approvals
    'approve_under_100k': ['admin', 'manager', 'operations'],
    'approve_over_100k': ['admin', 'manager'],
    'approve_over_500k': ['admin'],
    'compliance_approval': ['admin', 'compliance'],

    # Document Management
    'upload_documents': ['admin', 'manager', 'operations'],
    'delete_documents': ['admin', 'manager'],
    'view_documents': ['admin', 'manager', 'compliance', 'operations'],

    # User Management
    'create_user': ['admin'],
    'edit_user': ['admin'],
    'delete_user': ['admin'],
    'view_users': ['admin', 'manager'],

    # Reporting
    'view_reports': ['admin', 'manager', 'compliance'],
    'export_data': ['admin', 'compliance'],
    'run_audit_reports': ['admin', 'compliance'],

    # System
    'access_admin_panel': ['admin'],
    'modify_settings': ['admin'],
    'view_audit_log': ['admin', 'compliance'],

    # Special Permissions
    'initiate_payment': ['admin', 'manager'],  # Link to bank's payment system
    'manual_verification': ['admin', 'compliance'],
}

# =================== PERMISSION CHECK FUNCTIONS ===================

def get_user_role():
    """Get current user's role from session"""
    return session.get('user_role', None)

def has_permission(permission_name):
    """Check if current user has a specific permission"""
    user_role = get_user_role()

    if not user_role:
        return False

    # Admin has all permissions
    if user_role == 'admin':
        return True

    # Check if role has this specific permission
    allowed_roles = PERMISSIONS.get(permission_name, [])
    return user_role in allowed_roles

def get_user_permissions():
    """Get all permissions for current user"""
    user_role = get_user_role()

    if not user_role:
        return []

    # Admin gets all permissions
    if user_role == 'admin':
        return list(PERMISSIONS.keys())

    # Get permissions for this role
    user_perms = []
    for perm, roles in PERMISSIONS.items():
        if user_role in roles:
            user_perms.append(perm)

    return user_perms

def can_approve_amount(amount):
    """Check if user can approve a claim of given amount"""
    user_role = get_user_role()

    if not user_role:
        return False

    if amount < 100000:
        return has_permission('approve_under_100k')
    elif amount < 500000:
        return has_permission('approve_over_100k')
    else:
        return has_permission('approve_over_500k')

# =================== DECORATORS ===================

def require_permission(permission_name):
    """Decorator to require a specific permission for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(permission_name):
                # Check if this is an API call
                if request.path.startswith('/institution/api/'):
                    return jsonify({
                        'error': 'Permission denied',
                        'required_permission': permission_name
                    }), 403

                # Web page - redirect to dashboard with error
                return redirect(url_for('institution_dashboard', error='permission_denied'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(allowed_roles):
    """Decorator to require one of the specified roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = get_user_role()

            if user_role not in allowed_roles:
                if request.path.startswith('/institution/api/'):
                    return jsonify({
                        'error': 'Access denied',
                        'required_roles': allowed_roles
                    }), 403

                return redirect(url_for('institution_dashboard', error='access_denied'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_approval_level(amount):
    """Decorator to check if user can approve a specific amount"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not can_approve_amount(amount):
                if request.path.startswith('/institution/api/'):
                    return jsonify({
                        'error': 'Insufficient approval authority',
                        'amount': amount
                    }), 403

                return redirect(url_for('institution_dashboard', error='insufficient_approval'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =================== HELPER FUNCTIONS ===================

def get_role_info(role):
    """Get information about a role"""
    return ROLES.get(role, {
        'name': 'Unknown',
        'description': 'Unknown role',
        'level': 0
    })

def get_accessible_cases(user_id, user_role):
    """
    Determine which cases a user can access based on their role.

    Returns: SQL WHERE clause and parameters
    """
    if user_role in ['admin', 'manager', 'compliance']:
        # Can see all cases
        return "", []
    else:
        # Operations: Only see assigned cases (would need assignment table in production)
        # For now, they can see all pending cases
        return "WHERE status = 'pending' OR status = 'under_review'", []

def get_dashboard_metrics(user_role):
    """Get which metrics to show on dashboard based on role"""
    base_metrics = ['total_cases', 'pending_cases', 'cases_this_week']

    if user_role in ['admin', 'manager']:
        return base_metrics + ['avg_processing_time', 'approval_rate', 'total_disbursed']
    elif user_role == 'compliance':
        return base_metrics + ['compliance_reviews_needed', 'audit_items']
    else:
        return ['my_assigned_cases', 'my_completed_today']
