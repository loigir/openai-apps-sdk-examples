# Security Guidelines - AllôBye MCP Server

## Critical Security Notice

**IMMEDIATE ACTION REQUIRED**: If you have committed the `.env` file with real secrets to version control, follow the [Incident Response](#incident-response) section immediately.

## Table of Contents

1. [Environment Variable Management](#environment-variable-management)
2. [Secret Rotation Procedures](#secret-rotation-procedures)
3. [Access Control](#access-control)
4. [Security Best Practices](#security-best-practices)
5. [Incident Response](#incident-response)
6. [Compliance & Audit](#compliance--audit)

---

## Environment Variable Management

### Required Environment Variables

The following environment variables are **REQUIRED** for the server to function:

```bash
SUPABASE_URL                    # Supabase project URL
SUPABASE_SERVICE_ROLE_KEY      # Service role key (CRITICAL - bypass RLS)
SUPABASE_ANON_KEY              # Anonymous key (public-facing)
DATABASE_URL                    # Direct database connection string
SUPABASE_DB_PASSWORD           # Database password
```

### Optional Environment Variables

```bash
SUPABASE_PROJECT_REF           # Project reference ID
MOTION_PLUS_API_KEY            # Motion+ integration (if used)
ENVIRONMENT                     # Deployment environment (production/staging/dev)
LOG_LEVEL                      # Logging verbosity (INFO/DEBUG/WARNING/ERROR)
```

### Setup Instructions

1. **Never commit the `.env` file** - It is already in `.gitignore` to prevent accidental commits.

2. **Copy the example file**:
   ```bash
   cp .env.example .env
   ```

3. **Obtain credentials from Supabase**:
   - Navigate to your Supabase project dashboard
   - Go to **Project Settings** > **API**
   - Copy the required keys:
     - `SUPABASE_URL`: Project URL
     - `SUPABASE_ANON_KEY`: Under "Project API keys" (anon/public)
     - `SUPABASE_SERVICE_ROLE_KEY`: Under "Project API keys" (service_role) ⚠️
   - Go to **Project Settings** > **Database**
   - Copy the connection string and extract the password

4. **Set permissions on .env file** (Linux/Mac):
   ```bash
   chmod 600 .env
   ```

5. **Validate configuration**:
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✓ Environment loaded')"
   ```

### Security Validation

The server validates required environment variables on startup (see `get_supabase()` in `main.py`):

```python
if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
```

---

## Secret Rotation Procedures

### When to Rotate Secrets

Rotate secrets immediately if:

1. **Suspected compromise** - Secret may have been exposed
2. **Staff departure** - Team member with access leaves
3. **Scheduled rotation** - Every 90 days (recommended)
4. **Security audit** - Post-audit remediation
5. **Git exposure** - Secret committed to version control

### Rotation Checklist

#### 1. Supabase Service Role Key

**Impact**: CRITICAL - This key bypasses Row Level Security (RLS)

**Steps**:
1. Log into Supabase Dashboard
2. Navigate to **Project Settings** > **API**
3. Click **Reset Service Role Key**
4. Update `.env` file with new key:
   ```bash
   SUPABASE_SERVICE_ROLE_KEY=new_key_here
   ```
5. Restart the server:
   ```bash
   sudo systemctl restart allobye-server  # systemd
   # or
   pkill -HUP -f "uvicorn main:app"      # manual
   ```
6. Verify functionality:
   ```bash
   curl http://localhost:8000/health
   ```
7. **Document the rotation** in your security log

#### 2. Supabase Anonymous Key

**Impact**: MEDIUM - Public-facing key with RLS protection

**Steps**:
1. Navigate to **Project Settings** > **API** > **Reset Anon Key**
2. Update `.env` file
3. Update any client applications using this key
4. Restart the server

#### 3. Database Password

**Impact**: CRITICAL - Direct database access

**Steps**:
1. Navigate to **Project Settings** > **Database** > **Reset Database Password**
2. Update both `DATABASE_URL` and `SUPABASE_DB_PASSWORD` in `.env`:
   ```bash
   DATABASE_URL=postgresql://postgres:NEW_PASSWORD@db.xxxxx.supabase.co:5432/postgres
   SUPABASE_DB_PASSWORD=NEW_PASSWORD
   ```
3. Restart the server
4. Verify database connectivity

#### 4. Motion+ API Key

**Impact**: LOW - Third-party integration only

**Steps**:
1. Log into Motion+ dashboard
2. Navigate to API settings
3. Regenerate API key
4. Update `.env` file
5. Test integration

### Rotation Schedule

| Secret | Frequency | Automated | Priority |
|--------|-----------|-----------|----------|
| Service Role Key | 90 days | No | CRITICAL |
| Database Password | 90 days | No | CRITICAL |
| Anon Key | 180 days | No | MEDIUM |
| Motion+ API Key | 180 days | No | LOW |

---

## Access Control

### Service Role Key Usage

The `SUPABASE_SERVICE_ROLE_KEY` is **extremely sensitive** because it:

- **Bypasses Row Level Security (RLS)** - Can access all data
- **Has admin privileges** - Can modify database schema
- **No rate limiting** - Can perform unlimited operations

**Use Cases** (server-side only):
- ✅ Server-to-database operations
- ✅ Administrative tasks
- ✅ Backend MCP tool operations

**Never**:
- ❌ Send to client-side code
- ❌ Include in public APIs
- ❌ Store in client storage (localStorage, cookies)
- ❌ Log in application logs
- ❌ Include in error messages

### Authentication Flow

```
User Request → ChatGPT → MCP Tool
                            ↓
                    Validate access_token
                            ↓
                    Check permissions (role, ownership)
                            ↓
                    Use SERVICE_ROLE_KEY for DB query
                            ↓
                    Return filtered results
```

### Role-Based Access Control (RBAC)

The application enforces roles:

- **parent** - Can manage own children, delegates, emergencies
- **school_staff** - Can view school dashboard, pickup queue

Enforcement points:
- `require_auth()` - Validates authentication and role
- `verify_parent_owns_child()` - Ownership verification
- `verify_staff_at_school()` - School association verification

---

## Security Best Practices

### Development Environment

1. **Use separate Supabase projects** for dev/staging/production
2. **Never use production secrets** in development
3. **Use test data** - No real PII in development
4. **Local .env files** - Never share via Slack, email, etc.

### Production Environment

1. **Environment variables** should be set via:
   - **Systemd environment files** (Linux)
   - **Docker secrets** (containerized)
   - **Cloud provider secret managers** (AWS Secrets Manager, Google Secret Manager)
   - **Kubernetes secrets** (K8s deployments)

2. **Monitoring**:
   - Enable audit logging in Supabase
   - Monitor for unusual access patterns
   - Set up alerts for authentication failures

3. **Network Security**:
   - Use TLS/HTTPS for all connections
   - Restrict database access to server IP only
   - Use VPC/private subnets for production

### Code Review Checklist

Before committing code, verify:

- [ ] No secrets in code
- [ ] No secrets in comments
- [ ] No secrets in error messages
- [ ] No secrets in log statements
- [ ] `.env` not staged for commit
- [ ] Only `.env.example` has placeholder values

---

## Incident Response

### Git Exposure Incident

If the `.env` file or secrets were committed to version control:

#### Immediate Actions (within 1 hour)

1. **Rotate ALL secrets immediately** (see [Rotation Procedures](#secret-rotation-procedures))

2. **Remove from Git history**:
   ```bash
   # Remove file from history
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch allobye_server_python/.env' \
     --prune-empty --tag-name-filter cat -- --all

   # Or use BFG Repo-Cleaner (recommended)
   bfg --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive

   # Force push (coordinate with team first!)
   git push --force --all
   ```

3. **Verify removal**:
   ```bash
   git log --all --full-history --oneline -- allobye_server_python/.env
   ```

4. **Notify team** - Inform all developers to re-clone repository

#### Investigation (within 24 hours)

5. **Audit Supabase logs**:
   - Check for unauthorized access
   - Review recent database queries
   - Identify any data exfiltration

6. **Document incident**:
   - When was secret exposed?
   - How long was it public?
   - Who had access?
   - What actions were taken?

#### Follow-up (within 1 week)

7. **Security review**:
   - Audit all access logs
   - Review user accounts
   - Check for unauthorized changes

8. **Process improvement**:
   - Add pre-commit hooks (see below)
   - Update team training
   - Review access controls

### Pre-commit Hook (Prevention)

Install a pre-commit hook to prevent secret commits:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# Check for .env files
if git diff --cached --name-only | grep -E "\.env$" | grep -v "\.env\.example$"; then
    echo "ERROR: Attempting to commit .env file!"
    echo "Please remove it from staging: git reset HEAD .env"
    exit 1
fi

# Check for common secret patterns
if git diff --cached | grep -E "(SUPABASE_SERVICE_ROLE_KEY|password|secret|api[_-]?key)" | grep -v "\.env\.example"; then
    echo "WARNING: Potential secret detected in commit"
    echo "Please review your changes carefully"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
EOF

chmod +x .git/hooks/pre-commit
```

---

## Compliance & Audit

### Security Audit Log

Maintain a log of security events:

```
Date       | Event                | Action Taken           | By
-----------|---------------------|------------------------|--------
2025-11-04 | Service key rotated | Updated production env | Admin
2025-11-04 | .env git exposure   | Keys rotated, removed  | DevOps
```

### Access Audit

Regularly review who has access to:

- Supabase project (Project Settings > Team)
- Production server
- Database directly
- Environment variable storage (secrets manager)

### Compliance Requirements

For production deployments handling PII:

- **GDPR** (if EU users) - Data encryption, access controls, audit logs
- **PIPEDA** (Canada) - Consent, security safeguards, breach notification
- **SOC 2** (if required) - Access controls, encryption, monitoring

---

## Quick Reference

### Emergency Contacts

```
Security Issue: [Your security team contact]
Supabase Support: support@supabase.io
Incident Response: [Your incident response team]
```

### Useful Commands

```bash
# Check if .env is git-ignored
git check-ignore -v .env

# Verify environment variables loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('SERVICE_ROLE_KEY:', 'SET' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'NOT SET')"

# Test database connection
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY')); print('✓ Connected')"

# Server health check
curl http://localhost:8000/health
```

---

## Additional Resources

- [Supabase Security Best Practices](https://supabase.com/docs/guides/api/api-keys)
- [OWASP Secret Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App - Config](https://12factor.net/config)

---

**Last Updated**: 2025-11-04
**Version**: 1.0
**Owner**: AllôBye Security Team
