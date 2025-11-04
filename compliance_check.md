# Compliance Check - Loi 25 (Quebec Privacy Law)

**Date**: 2025-11-04
**System**: AllôBye School Pickup Coordination System
**Regulation**: Loi 25 - Loi modernisant des dispositions législatives en matière de protection des renseignements personnels
**Assessor**: Security Analysis Agent

---

## Executive Summary

AllôBye handles **highly sensitive personal information** about **children**, which falls under the strictest requirements of Quebec's Loi 25 (Law 25).

**Overall Compliance Status**: ❌ **NON-COMPLIANT**

**Critical Gaps**: 8
**High Priority Gaps**: 6
**Medium Priority Gaps**: 4

**Risk Level**: **HIGH** - System should not process real child data until compliance gaps addressed

**Effective Date**: September 22, 2023 (most provisions)
**Final Deadline**: September 22, 2024 (all provisions must be compliant)

---

## Article-by-Article Compliance Assessment

### Section 1: Consent and Collection (Articles 8-14)

#### Article 8: Consent for Collection, Use, and Communication

**Requirement**: Personal information must be collected, used, or communicated with the consent of the person concerned.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No explicit consent mechanism implemented
- No consent management interface
- No consent records in database
- No ability for parents to view/manage consent

**Evidence**:
```sql
-- schema.sql: No consent tracking table
-- Missing:
-- CREATE TABLE consent_records (
--     id UUID PRIMARY KEY,
--     user_id UUID NOT NULL,
--     purpose TEXT NOT NULL,
--     granted BOOLEAN NOT NULL,
--     granted_at TIMESTAMP,
--     expires_at TIMESTAMP
-- );
```

**Findings**:
1. **No Consent Collection**: Account creation doesn't request consent for data processing
2. **No Purpose Specification**: Users not informed why data is collected
3. **No Granular Consent**: Cannot consent to specific uses (e.g., medical info sharing)

**Required Actions**:
1. Add consent management UI to signup flow
2. Create `consent_records` table
3. Implement consent versioning (changes require re-consent)
4. Add ability to withdraw consent
5. Document all data processing purposes

**Priority**: CRITICAL
**Deadline**: Immediate

---

#### Article 9: Collection of Sensitive Information

**Requirement**: Sensitive information (health, biometric, etc.) requires **explicit** consent and must be **necessary** for declared purposes.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- Medical information collected without explicit consent
- No justification documented for why medical info is necessary
- No separate consent for sensitive data

**Evidence**:
```sql
-- schema.sql:49
medical_info TEXT,  -- Collected without explicit consent
```

```python
# auth.py: No separate consent for medical data
# No distinction between regular and sensitive data
```

**Findings**:
1. **Medical Data Collection**: No explicit consent for medical information
2. **No Necessity Justification**: System doesn't document why medical info is needed
3. **No Opt-Out Option**: Parents cannot refuse medical info while using core features

**Required Actions**:
1. Add separate consent checkbox for medical information
2. Document necessity (e.g., "for emergency response")
3. Make medical info optional if not essential
4. Provide clear explanation of how medical data is used
5. Allow parents to update/delete medical info

**Example Consent Form**:
```
☐ I consent to AllôBye collecting and storing my child's medical information
  (allergies, medications, health conditions) for emergency response purposes.

  This information will only be shared with:
  - Authorized school personnel
  - Emergency responders (in case of medical emergency)
  - Authorized pickup delegates (if parent grants permission)

  You can withdraw this consent at any time in Settings.
```

**Priority**: CRITICAL
**Deadline**: Immediate

---

#### Article 10: Information to be Provided

**Requirement**: Person must be informed of:
- Purpose of collection
- Means of collection
- Right to access and rectification
- Authority for collection
- Who will have access

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No privacy notice displayed
- No information about data processing
- No rights notification
- No contact information for privacy inquiries

**Required Actions**:
1. Create comprehensive Privacy Notice
2. Display notice before account creation
3. Include all required information
4. Make notice easily accessible (link in footer)
5. Version control for policy changes

**Example Privacy Notice Template**:

```markdown
# AllôBye Privacy Notice

## 1. Purpose of Collection
We collect your personal information to:
- Coordinate safe pickup of your children from school
- Authorize trusted delegates to pick up your children
- Notify relevant parties in case of emergency
- Comply with school safety regulations

## 2. Information We Collect
- **Child Information**: Name, grade, school, medical information (optional)
- **Parent Information**: Name, email, phone number
- **Delegate Information**: Name, email, phone number, authorized permissions
- **Pickup Records**: Scheduled times, actual pickup times, status updates
- **Emergency Information**: Emergency type, context, notifications sent

## 3. How We Collect Information
- Directly from you during account registration
- From your interactions with our system (scheduling pickups, etc.)
- From school personnel when verifying pickup completion

## 4. Who Has Access to Your Information
- **You**: Full access to your child's information
- **Authorized Delegates**: Limited access to pickup schedules for authorized children
- **School Personnel**: Access to pickup queues and emergency notifications for their school
- **System Administrators**: Technical access for system maintenance (logged and audited)

## 5. How We Protect Your Information
- Encryption in transit (HTTPS/TLS)
- Encryption at rest for sensitive data
- Role-based access controls
- Regular security audits
- 24/7 monitoring and logging

## 6. Your Rights
You have the right to:
- Access your personal information
- Correct inaccurate information
- Request deletion of your information
- Withdraw consent at any time
- Port your data to another service
- File a complaint with the CAI (Commission d'accès à l'information)

## 7. How to Exercise Your Rights
Contact us at: privacy@allobye.ca
Or write to:
  AllôBye Privacy Officer
  [Address]
  [City, Province, Postal Code]

We will respond within 30 days.

## 8. Data Retention
- Active pickups: Retained for 90 days after completion
- Emergency records: Retained for 30 days after resolution
- Audit logs: Retained for 1 year
- Account information: Retained until account deletion requested

## 9. Legal Authority
This collection is authorized by:
- Parental consent
- Quebec Education Act (school safety requirements)
- Loi 25 (Quebec privacy law)

## 10. Contact Information
**Privacy Officer**: privacy@allobye.ca
**Technical Support**: support@allobye.ca
**CAI (Regulator)**: 1-888-528-7741 or www.cai.gouv.qc.ca

Last Updated: 2025-11-04
Version: 1.0
```

**Priority**: CRITICAL
**Deadline**: Immediate

---

### Section 2: Security Safeguards (Articles 12-13)

#### Article 12: Security Safeguards

**Requirement**: Protection measures proportional to sensitivity of information.

**Status**: ⚠️ **PARTIALLY COMPLIANT**

**Current State**:
✅ **Compliant**:
- HTTPS/TLS for data in transit
- JWT authentication
- Row-Level Security (RLS) policies
- Structured logging and monitoring

❌ **Non-Compliant**:
- Medical information not encrypted at rest (CRITICAL)
- PII (phone, email) not encrypted at rest
- Secrets in plaintext .env files
- No encryption key rotation policy
- No data masking for logs

**Evidence**:
```sql
-- VULNERABLE: Medical data in plaintext
medical_info TEXT,  -- Should be: medical_info BYTEA (encrypted)
```

**Required Actions**:
1. Encrypt all sensitive data at rest (medical info, PII)
2. Implement encryption key management (AWS KMS, Vault)
3. Establish key rotation policy (quarterly)
4. Add data masking for logs
5. Implement audit trail for all access to sensitive data
6. Conduct annual penetration testing
7. Maintain incident response plan

**Compliance Matrix**:

| Control | Required | Implemented | Status |
|---------|----------|-------------|--------|
| Encryption in Transit | Yes | Yes (HTTPS) | ✅ |
| Encryption at Rest | Yes | No | ❌ |
| Access Controls | Yes | Yes (RLS) | ✅ |
| Authentication | Yes | Yes (JWT) | ✅ |
| Audit Logging | Yes | Partial | ⚠️ |
| Key Management | Yes | No | ❌ |
| Incident Response | Yes | No | ❌ |
| Penetration Testing | Yes | No | ❌ |

**Priority**: CRITICAL
**Deadline**: Immediate (encryption), 30 days (other controls)

---

#### Article 13: Breach Notification

**Requirement**: Must notify CAI and affected individuals of serious data breaches within **reasonable time**.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No breach detection mechanism
- No incident response plan
- No breach notification procedure
- No CAI contact established

**Required Actions**:
1. Establish breach detection monitoring
2. Create incident response plan
3. Document breach notification procedure
4. Train staff on breach response
5. Establish CAI contact

**Incident Response Plan Template**:

```markdown
# AllôBye Data Breach Response Plan

## 1. Detection
**Triggers**:
- Unusual database access patterns
- Authentication anomalies
- Security alerts from monitoring systems
- External notification (security researcher, customer)

**Monitoring**:
- Real-time alerts for RLS policy violations
- Failed authentication attempt monitoring
- Database query anomaly detection
- File integrity monitoring

## 2. Assessment (Within 24 Hours)
**Questions to Answer**:
- What data was accessed/exfiltrated?
- How many individuals affected?
- What is the sensitivity of the data?
- Is there risk of harm to individuals?

**Severity Classification**:
- **CRITICAL**: Medical data, 100+ individuals, or children involved
- **HIGH**: PII for 50+ individuals
- **MEDIUM**: Limited PII, <50 individuals
- **LOW**: No PII, technical data only

## 3. Containment (Immediate)
- Isolate affected systems
- Revoke compromised credentials
- Block malicious IPs
- Preserve forensic evidence

## 4. Notification (As Required)

**CAI Notification** (if serious breach):
- **Deadline**: As soon as possible, no later than when notifying individuals
- **Method**: CAI online portal or email: incidents@cai.gouv.qc.ca
- **Information Required**:
  - Description of breach
  - Date of breach
  - Number of affected individuals
  - Type of information involved
  - Circumstances of breach
  - Measures taken to reduce risk
  - Measures taken to notify individuals

**Individual Notification** (if risk of serious harm):
- **Deadline**: As soon as possible
- **Method**: Direct email, phone call, or registered mail
- **Information to Include**:
  - Description of breach
  - Type of information involved
  - Measures taken to reduce risk
  - Measures individual can take
  - Contact information for questions

**Public Notification** (if direct notification impossible):
- Post on website
- Public notice in media
- Social media announcement

## 5. Remediation
- Fix vulnerability
- Review and update security controls
- Conduct post-mortem analysis
- Update incident response plan

## 6. Reporting
- Document all actions taken
- Maintain incident log
- Report to executive team and board
- Annual summary to CAI

## Contact Information
**Privacy Officer**: privacy@allobye.ca
**CAI**: incidents@cai.gouv.qc.ca / 1-888-528-7741
**Legal Counsel**: [TBD]
**PR Team**: [TBD]
```

**Priority**: HIGH
**Deadline**: 30 days

---

### Section 3: Individual Rights (Articles 27-41)

#### Article 27: Right of Access

**Requirement**: Individual has right to access their personal information.

**Status**: ⚠️ **PARTIALLY COMPLIANT**

**Current State**:
✅ **Compliant**:
- `auth-profile` tool allows users to view their profile
- Users can see their own pickups and delegate authorizations

❌ **Non-Compliant**:
- No comprehensive data export
- No ability to see ALL data processed (logs, metadata)
- No ability to see data access history
- Response time not guaranteed within 30 days

**Evidence**:
```python
# auth.py:432
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    # ⚠️ Returns only profile data, not complete data set
    return {
        "id": profile["id"],
        "email": profile["email"],
        # ... missing: pickups, emergencies, audit logs, etc.
    }
```

**Required Actions**:
1. Create comprehensive data export tool
2. Include ALL personal information:
   - Profile data
   - Children information
   - Delegate authorizations
   - Pickup history
   - Emergency history
   - Audit logs (access history)
   - Consent records
3. Implement 30-day response SLA
4. Provide data in structured format (JSON, CSV)
5. Document data export procedure

**Implementation**:
```python
@mcp.tool("data-export-request")
async def request_data_export(access_token: str):
    """Request complete data export (Loi 25 Article 27)."""
    user = await validate_session(access_token)

    # Generate comprehensive export
    export_data = {
        "profile": await get_user_profile(user.id),
        "children": await get_user_children(user.id),
        "delegates": await get_user_delegates(user.id),
        "pickups": await get_user_pickups(user.id),
        "emergencies": await get_user_emergencies(user.id),
        "audit_logs": await get_user_audit_logs(user.id),
        "consent_records": await get_user_consents(user.id),
        "export_date": datetime.now().isoformat(),
        "export_format_version": "1.0"
    }

    # Log export request
    await log_audit_event(
        action="data_export_requested",
        entity_type="user",
        entity_id=user.id,
        user=user
    )

    return {
        "data": export_data,
        "format": "json",
        "rights_notice": "You have the right to access, correct, and delete this information."
    }
```

**Priority**: HIGH
**Deadline**: 30 days

---

#### Article 28: Right to Rectification

**Requirement**: Individual can request correction of inaccurate information.

**Status**: ⚠️ **PARTIALLY COMPLIANT**

**Current State**:
✅ **Compliant**:
- Users can update profile name
- Users can modify school associations

❌ **Non-Compliant**:
- No ability to correct child information
- No formal rectification request process
- No notification when corrections made
- No audit trail of corrections

**Required Actions**:
1. Add UI to edit child information
2. Add UI to edit delegate information
3. Create formal correction request process
4. Log all corrections in audit trail
5. Notify affected parties of corrections (if necessary)

**Priority**: MEDIUM
**Deadline**: 60 days

---

#### Article 28.1: Right to Deletion (Right to be Forgotten)

**Requirement**: Individual can request deletion of personal information in certain circumstances.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No account deletion mechanism
- No data deletion workflow
- No retention policy documented
- No ability to delete specific data items

**Evidence**:
```sql
-- schema.sql: No soft delete mechanism
-- Missing:
-- ALTER TABLE children ADD COLUMN deleted_at TIMESTAMP;
-- ALTER TABLE delegates ADD COLUMN deleted_at TIMESTAMP;
```

**Required Actions**:
1. Implement account deletion workflow
2. Create "Delete My Account" UI
3. Implement soft delete for audit compliance
4. Define retention periods for deleted data
5. Purge deleted data after retention period
6. Notify user of deletion completion
7. Handle deletion requests within 30 days

**Implementation**:
```python
@mcp.tool("account-deletion-request")
async def request_account_deletion(
    reason: str,
    delete_children_data: bool,
    access_token: str,
):
    """Request account deletion (Loi 25 Article 28.1)."""
    user = await validate_session(access_token)

    # Create deletion request
    deletion_request = {
        "id": str(uuid4()),
        "user_id": user.id,
        "requested_at": datetime.now().isoformat(),
        "reason": reason,
        "status": "pending",
        "delete_children_data": delete_children_data,
        "estimated_completion": (datetime.now() + timedelta(days=30)).isoformat()
    }

    supabase.table("deletion_requests").insert(deletion_request).execute()

    # Log request
    await log_audit_event(
        action="account_deletion_requested",
        entity_type="user",
        entity_id=user.id,
        user=user,
        new_value=deletion_request
    )

    # Send confirmation email
    await send_email(
        to=user.email,
        subject="Demande de suppression de compte - AllôBye",
        body=f"""
        Votre demande de suppression de compte a été reçue.

        Numéro de demande: {deletion_request['id']}
        Date de traitement estimée: {deletion_request['estimated_completion']}

        Vos données seront supprimées conformément à la Loi 25.

        Si vous n'avez pas fait cette demande, contactez-nous immédiatement.
        """
    )

    return {
        "request_id": deletion_request["id"],
        "status": "pending",
        "message": "Votre demande sera traitée dans un délai de 30 jours."
    }


async def process_deletion_request(request_id: str):
    """Process approved deletion request."""
    request = supabase.table("deletion_requests").select("*").eq("id", request_id).single().execute()

    if request.data["status"] != "approved":
        return

    user_id = request.data["user_id"]

    # Soft delete user data
    supabase.table("user_profiles").update({
        "deleted_at": datetime.now().isoformat(),
        "email": f"deleted_{user_id}@deleted.local",  # Anonymize
        "name": "[Deleted User]"
    }).eq("id", user_id).execute()

    if request.data["delete_children_data"]:
        # Soft delete children
        supabase.table("children").update({
            "deleted_at": datetime.now().isoformat(),
            "name": "[Deleted]",
            "medical_info": None,
            "parent_email": f"deleted_{user_id}@deleted.local"
        }).eq("parent_email", request.data["user_email"]).execute()

    # Mark deletion complete
    supabase.table("deletion_requests").update({
        "status": "completed",
        "completed_at": datetime.now().isoformat()
    }).eq("id", request_id).execute()

    # Send confirmation
    # (Email sent to alternate contact provided during deletion request)
```

**Retention Schedule**:
```
Soft-deleted data retention:
- User profiles: 1 year (for legal compliance, dispute resolution)
- Children data: 1 year
- Audit logs: 7 years (legal requirement)
- Pickup records: 90 days (operational need)

After retention period:
- Hard delete from production database
- Remove from backups (next backup cycle)
- Purge from all systems
```

**Priority**: CRITICAL
**Deadline**: Immediate

---

#### Article 28.2: Right to Data Portability

**Requirement**: Individual can obtain their information in a structured, commonly used format.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No data export in standard format
- No ability to transfer data to competitor

**Required Actions**:
1. Implement data export in JSON and CSV formats
2. Provide complete data set (see Article 27)
3. Make export easily downloadable
4. Document export format for interoperability

**Implementation**:
```python
@mcp.tool("data-portability-export")
async def export_portable_data(
    format: str = "json",  # "json" or "csv"
    access_token: str,
):
    """Export data in portable format (Loi 25 Article 28.2)."""
    user = await validate_session(access_token)

    # Get all user data
    data = await get_complete_user_data(user.id)

    if format == "json":
        return {
            "format": "json",
            "version": "1.0",
            "standard": "AllôBye Data Export Standard",
            "exported_at": datetime.now().isoformat(),
            "data": data
        }
    elif format == "csv":
        # Convert to CSV format
        csv_files = {
            "profile.csv": convert_to_csv(data["profile"]),
            "children.csv": convert_to_csv(data["children"]),
            "pickups.csv": convert_to_csv(data["pickups"]),
        }
        return {
            "format": "csv",
            "files": csv_files
        }
```

**Priority**: HIGH
**Deadline**: 30 days

---

### Section 4: Governance and Accountability (Articles 3.1-3.7)

#### Article 3.1: Privacy Policy Required

**Requirement**: Every organization must establish and implement privacy policies.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No formal privacy policy documented
- No privacy governance framework
- No privacy officer designated

**Required Actions**:
1. Draft comprehensive Privacy Policy
2. Establish Privacy Governance Framework
3. Designate Privacy Officer
4. Create Privacy Management Program
5. Publish policy on website
6. Train staff on privacy policies

**Privacy Policy Requirements (Loi 25)**:
```markdown
# AllôBye Privacy Policy

Must include:

1. **Governance Structure**
   - Privacy Officer designation
   - Roles and responsibilities
   - Reporting structure

2. **Data Processing Principles**
   - Lawfulness, fairness, transparency
   - Purpose limitation
   - Data minimization
   - Accuracy
   - Storage limitation
   - Integrity and confidentiality

3. **Data Collection Practices**
   - What we collect
   - Why we collect it
   - How we collect it
   - Who has access

4. **Security Measures**
   - Technical safeguards
   - Organizational safeguards
   - Employee training

5. **Individual Rights**
   - Right of access
   - Right to rectification
   - Right to deletion
   - Right to portability
   - How to exercise rights

6. **Breach Response**
   - Breach notification procedures
   - Incident response plan
   - Contact information

7. **International Transfers**
   - If data transferred outside Quebec
   - Safeguards in place

8. **Contact Information**
   - Privacy Officer
   - CAI (regulator)
   - Complaint process

9. **Policy Updates**
   - Version control
   - Change notification process
   - Effective date
```

**Privacy Officer Responsibilities**:
- Oversee privacy compliance
- Handle access requests
- Investigate privacy complaints
- Conduct privacy impact assessments
- Report to CAI as required
- Train employees on privacy
- Maintain privacy documentation

**Priority**: CRITICAL
**Deadline**: Immediate

---

#### Article 3.2: Privacy Impact Assessment (PIA)

**Requirement**: PIA required for certain high-risk processing activities.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No Privacy Impact Assessment conducted
- High-risk processing (children's data, medical info) without PIA

**Evidence**:
AllôBye processes:
- Children's personal information (HIGH RISK)
- Medical information (HIGH RISK)
- Real-time location tracking (HIGH RISK)
- Automated emergency notifications (HIGH RISK)

**Required Actions**:
1. Conduct comprehensive Privacy Impact Assessment
2. Identify and mitigate privacy risks
3. Document PIA findings
4. Implement recommended safeguards
5. Review PIA annually or when system changes

**PIA Template**:
```markdown
# Privacy Impact Assessment - AllôBye

## 1. Project Description
- **System**: AllôBye School Pickup Coordination
- **Purpose**: Safe coordination of child pickups
- **Data Processed**: Children's data, medical info, location, emergency notifications

## 2. Privacy Risks Identified

### Risk 1: Unauthorized Access to Medical Information
- **Likelihood**: Medium
- **Impact**: High
- **Severity**: HIGH
- **Mitigation**:
  - Encrypt medical data at rest
  - Implement strict access controls
  - Audit all access to medical information

### Risk 2: Data Breach Exposing Children's Information
- **Likelihood**: Low
- **Impact**: Critical
- **Severity**: HIGH
- **Mitigation**:
  - Multi-layered security (JWT + RLS)
  - Regular penetration testing
  - Breach detection monitoring
  - Incident response plan

### Risk 3: Unauthorized Delegate Impersonation
- **Likelihood**: Low
- **Impact**: Critical (child safety)
- **Severity**: CRITICAL
- **Mitigation**:
  - Multi-factor authentication for delegate authorization
  - Photo verification at pickup
  - Real-time parent notifications

[Continue for all identified risks]

## 3. Compliance Assessment
- Loi 25: Gaps identified (see compliance checklist)
- PIPEDA: Not applicable (provincial jurisdiction)
- School regulations: To be verified

## 4. Recommendations
1. Implement encryption for all sensitive data
2. Add multi-factor authentication
3. Enhance audit logging
4. Establish data retention policy
5. Create privacy training program

## 5. Approval
- **Privacy Officer**: [Signature]
- **Legal Counsel**: [Signature]
- **CTO**: [Signature]
- **Date**: [Date]

## 6. Review Schedule
- **Next Review**: [Date + 1 year]
- **Trigger for Earlier Review**: Material system changes
```

**Priority**: CRITICAL
**Deadline**: Before production launch

---

### Section 5: Third-Party Data Sharing (Articles 18-19)

#### Article 18: Communication to Third Parties

**Requirement**: Personal information communicated to third parties must have legal basis.

**Status**: ⚠️ **PARTIALLY COMPLIANT**

**Current State**:
✅ **Compliant**:
- No data sold to third parties
- Limited sharing with school personnel (legitimate interest)

⚠️ **Needs Documentation**:
- Supabase (US company) - data processor agreement needed
- Backup services - need to be documented
- Monitoring services (if any) - need to be documented

**Required Actions**:
1. Inventory all third-party data recipients
2. Establish Data Processing Agreements (DPAs) with each
3. Document legal basis for each transfer
4. Add third-party disclosure to Privacy Notice
5. Conduct due diligence on third-party security

**Third-Party Inventory**:
```markdown
# Third-Party Data Processors

## 1. Supabase (PostgreSQL Hosting)
- **Location**: United States (AWS us-east-1)
- **Data Shared**: All application data
- **Purpose**: Database hosting and real-time services
- **Legal Basis**: Data processing agreement
- **Safeguards**:
  - Standard contractual clauses
  - Encryption in transit and at rest
  - SOC 2 Type II certified
  - GDPR compliant
- **DPA Status**: ❌ NEEDED
- **Risk**: HIGH (data residency outside Quebec)

## 2. AWS (if used for backups, secrets, etc.)
- **Location**: Canada (ca-central-1) or US
- **Data Shared**: Database backups, secrets
- **Purpose**: Backup and key management
- **Legal Basis**: Data processing agreement
- **Safeguards**:
  - Encryption at rest
  - Access controls
  - ISO 27001 certified
- **DPA Status**: ❌ NEEDED

## 3. Email Service Provider (for notifications)
- **Location**: [TBD]
- **Data Shared**: Email addresses, names
- **Purpose**: Transactional emails (password reset, notifications)
- **Legal Basis**: Legitimate interest
- **DPA Status**: ❌ NEEDED

## Recommendations:
1. Prioritize Quebec/Canadian data residency where possible
2. Establish DPAs with all processors
3. Conduct annual security reviews
4. Maintain processor register (Loi 25 requirement)
```

**Data Residency Concern**:
- Supabase may store data in US (depends on configuration)
- Loi 25 prefers Quebec/Canadian residency
- **Recommendation**: Migrate to Canadian Supabase region or Canadian cloud provider

**Priority**: HIGH
**Deadline**: 60 days

---

### Section 6: Data Retention and Destruction (Article 12)

#### Article 12: Destruction of Information

**Requirement**: Personal information must be destroyed when retention period expires or purpose achieved.

**Status**: ❌ **NON-COMPLIANT**

**Current State**:
- No documented retention schedule
- No automated deletion
- Data retained indefinitely

**Required Actions**:
1. Establish data retention schedule
2. Implement automated data deletion
3. Document destruction procedures
4. Log all deletions in audit trail

**Retention Schedule**:
```markdown
# AllôBye Data Retention Schedule

## Active User Data
| Data Type | Retention Period | Legal Basis |
|-----------|------------------|-------------|
| User profiles | Until account deleted | Consent |
| Children information | Until account deleted | Consent |
| Delegate authorizations | Until revoked or account deleted | Consent |
| Active pickups | 90 days after completion | Operational need |
| Resolved emergencies | 30 days after resolution | Operational need |
| Consent records | 7 years after last interaction | Legal requirement |
| Audit logs | 7 years | Legal requirement |

## Deleted User Data (Soft Delete)
| Data Type | Retention After Deletion | Reason |
|-----------|-------------------------|--------|
| User profiles (anonymized) | 1 year | Legal compliance, disputes |
| Children data (anonymized) | 1 year | Legal compliance |
| Audit logs | 7 years | Legal requirement |

## Backups
| Backup Type | Retention | Encryption |
|-------------|-----------|------------|
| Daily backups | 30 days | Yes (AES-256) |
| Weekly backups | 12 weeks | Yes |
| Monthly backups | 12 months | Yes |

## Destruction Procedures
1. **Automated Deletion**
   - Scheduled job runs daily at 2 AM
   - Deletes data past retention period
   - Logs all deletions

2. **Backup Purging**
   - Backups older than retention period deleted
   - Secure deletion (overwrite + delete)
   - Verified through monitoring

3. **User-Requested Deletion**
   - Processed within 30 days
   - Confirmation sent to user
   - Added to deletion log

4. **Verification**
   - Quarterly audit of retention compliance
   - Annual review of retention schedule
```

**Priority**: HIGH
**Deadline**: 60 days

---

## Compliance Gaps Summary

### CRITICAL Gaps (Must Fix Immediately)

1. **No Consent Management** (Article 8)
   - Action: Implement consent collection and management
   - Deadline: Before production launch

2. **Medical Data Not Encrypted** (Article 12)
   - Action: Encrypt all sensitive data at rest
   - Deadline: Immediate

3. **No Privacy Notice** (Article 10)
   - Action: Create and display comprehensive privacy notice
   - Deadline: Before production launch

4. **No Data Deletion Mechanism** (Article 28.1)
   - Action: Implement account deletion workflow
   - Deadline: Immediate

5. **No Privacy Policy** (Article 3.1)
   - Action: Draft and publish privacy policy
   - Deadline: Before production launch

6. **No Privacy Impact Assessment** (Article 3.2)
   - Action: Conduct comprehensive PIA
   - Deadline: Before production launch

### HIGH Priority Gaps (Fix Within 60 Days)

1. **No Data Export** (Articles 27, 28.2)
   - Action: Implement comprehensive data export

2. **No Breach Response Plan** (Article 13)
   - Action: Create incident response plan

3. **No Data Retention Policy** (Article 12)
   - Action: Establish and enforce retention schedule

4. **Missing Third-Party Agreements** (Article 18)
   - Action: Establish DPAs with all processors

5. **Data Residency Outside Quebec**
   - Action: Evaluate migration to Canadian infrastructure

### MEDIUM Priority Gaps (Fix Within 90 Days)

1. **No Rectification Process** (Article 28)
   - Action: Add UI to correct personal information

2. **Limited Audit Logging**
   - Action: Expand audit trail coverage

3. **No Privacy Training**
   - Action: Train all staff on privacy requirements

---

## Implementation Roadmap

### Phase 1: Critical Compliance (Weeks 1-2)

**Week 1**:
- [ ] Encrypt medical information at rest
- [ ] Draft Privacy Policy and Privacy Notice
- [ ] Implement consent management UI
- [ ] Designate Privacy Officer

**Week 2**:
- [ ] Conduct Privacy Impact Assessment
- [ ] Implement account deletion workflow
- [ ] Create breach response plan
- [ ] Establish data retention schedule

### Phase 2: High Priority (Weeks 3-8)

**Weeks 3-4**:
- [ ] Implement data export functionality
- [ ] Establish DPAs with third parties
- [ ] Set up automated data deletion

**Weeks 5-6**:
- [ ] Evaluate Canadian data residency options
- [ ] Enhance audit logging
- [ ] Create privacy training materials

**Weeks 7-8**:
- [ ] Conduct staff privacy training
- [ ] Test deletion workflows
- [ ] Perform compliance review

### Phase 3: Medium Priority (Weeks 9-12)

**Weeks 9-10**:
- [ ] Implement data rectification UI
- [ ] Expand audit trail coverage
- [ ] Document all privacy procedures

**Weeks 11-12**:
- [ ] Final compliance audit
- [ ] Remediate any remaining gaps
- [ ] Prepare for CAI audit (if required)

---

## Compliance Checklist

Use this checklist to track compliance progress:

### Consent and Collection
- [ ] Consent management system implemented
- [ ] Explicit consent for sensitive data (medical info)
- [ ] Privacy notice displayed before data collection
- [ ] Consent records maintained
- [ ] Ability to withdraw consent

### Security Safeguards
- [ ] Medical data encrypted at rest
- [ ] PII encrypted where appropriate
- [ ] Encryption key management implemented
- [ ] Access controls (RLS) in place
- [ ] Audit logging for sensitive data access
- [ ] Breach detection monitoring
- [ ] Incident response plan documented
- [ ] Annual penetration testing scheduled

### Individual Rights
- [ ] Right of access (data export)
- [ ] Right to rectification (edit UI)
- [ ] Right to deletion (account deletion)
- [ ] Right to portability (export formats)
- [ ] 30-day response SLA established

### Governance
- [ ] Privacy Officer designated
- [ ] Privacy Policy published
- [ ] Privacy Impact Assessment completed
- [ ] Privacy training program established
- [ ] Annual PIA review scheduled

### Third Parties
- [ ] All third-party processors inventoried
- [ ] DPAs established with processors
- [ ] Legal basis documented for each transfer
- [ ] Third-party security due diligence conducted

### Data Retention
- [ ] Retention schedule documented
- [ ] Automated deletion implemented
- [ ] Backup retention aligned with schedule
- [ ] Destruction procedures documented

### Documentation
- [ ] Privacy Policy (public)
- [ ] Privacy Notice (displayed to users)
- [ ] Privacy Impact Assessment (internal)
- [ ] Incident Response Plan (internal)
- [ ] Data Processing Agreements (with processors)
- [ ] Retention Schedule (internal)
- [ ] Employee training materials

---

## CAI (Commission d'accès à l'information) Interaction

### When to Contact CAI

**Mandatory**:
- Data breach with risk of serious harm
- Privacy Impact Assessment for high-risk processing (may be requested)
- Annual reporting (if required by CAI)

**Optional**:
- Guidance on compliance
- Pre-launch compliance review
- Complaint investigation

### CAI Contact Information
- **Website**: www.cai.gouv.qc.ca
- **Phone**: 1-888-528-7741 (toll-free)
- **Email**: incidents@cai.gouv.qc.ca (for breach notifications)
- **Address**:
  ```
  Commission d'accès à l'information du Québec
  525, boulevard René-Lévesque Est, bureau 1.20
  Québec (Québec) G1R 5S9
  ```

### Breach Notification to CAI

**Timeline**:
- Notify as soon as possible
- No later than when notifying affected individuals

**Information to Provide**:
1. Description of the breach
2. Date or period of the breach
3. Number of affected individuals
4. Type of information involved
5. Circumstances of the breach
6. Measures taken to reduce risk
7. Measures taken to notify individuals

**Submission Method**:
- Online portal: www.cai.gouv.qc.ca
- Email: incidents@cai.gouv.qc.ca
- By mail (for formal documentation)

---

## Penalties for Non-Compliance

Loi 25 includes significant penalties for violations:

**Administrative Penalties**:
- Up to **$10,000,000** or **2% of worldwide turnover** (whichever is greater)
- For serious violations involving children's data or medical information

**Criminal Penalties**:
- Fines for individuals: Up to $25,000
- Fines for corporations: Up to $50,000
- Prison terms for egregious violations

**Specific Violations**:
- Collecting information without consent: Up to $5,000 (individual) / $25,000 (corp)
- Failure to implement security safeguards: Up to $10,000 (individual) / $50,000 (corp)
- Failure to notify breach: Up to $15,000 (individual) / $100,000 (corp)
- Obstruction of CAI investigation: Up to $25,000 (individual) / $100,000 (corp)

**Reputational Risk**:
- Loss of parent trust
- Media coverage of violations
- School contract terminations
- Difficulty attracting new clients

---

## Recommendations

### Immediate Actions (This Week)

1. **Halt Production Deployment**
   - Do not process real child data until compliance gaps addressed

2. **Designate Privacy Officer**
   - Assign responsibility immediately
   - Empower to make compliance decisions

3. **Encrypt Medical Data**
   - Critical security and compliance gap
   - Implement field-level encryption

4. **Draft Privacy Policy**
   - Engage legal counsel
   - Publish before any data collection

### Short-Term Actions (30 Days)

1. **Conduct Privacy Impact Assessment**
   - Identify all privacy risks
   - Implement mitigation measures

2. **Implement Consent Management**
   - Collect explicit consent for all data processing
   - Especially for sensitive data (medical info)

3. **Create Breach Response Plan**
   - Establish CAI contact
   - Train staff on response procedures

4. **Establish Data Retention Policy**
   - Document retention periods
   - Implement automated deletion

### Medium-Term Actions (60-90 Days)

1. **Evaluate Canadian Data Residency**
   - Reduce regulatory risk
   - Align with Loi 25 preferences

2. **Establish Third-Party Agreements**
   - DPAs with all processors
   - Security due diligence

3. **Implement All User Rights**
   - Data export, deletion, rectification
   - 30-day response SLA

4. **Privacy Training Program**
   - Train all employees
   - Ongoing training for new hires

---

## Conclusion

AllôBye is currently **NON-COMPLIANT** with Quebec's Loi 25 due to critical gaps in:
- Consent management
- Data encryption
- Privacy documentation
- User rights implementation

**Risk Assessment**: **HIGH** - System should not process real child data until compliance gaps are addressed.

**Estimated Remediation Time**: 8-12 weeks for full compliance

**Estimated Cost**:
- Development effort: 4-6 weeks
- Legal review: $5,000-$10,000
- Privacy Officer (ongoing): $80,000-$120,000/year or part-time consultant
- Infrastructure changes (Canadian hosting): Variable

**Next Steps**:
1. Present findings to executive team
2. Obtain budget and resource approval
3. Begin Phase 1 implementation immediately
4. Engage privacy lawyer for policy review
5. Schedule CAI consultation (optional but recommended)

**Compliance Timeline**:
- **Today**: Halt production deployment
- **Week 1-2**: Critical fixes (encryption, policies)
- **Week 3-8**: High priority (user rights, third parties)
- **Week 9-12**: Final compliance verification
- **Week 13**: Production launch (compliant)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Next Review**: After implementation of Phase 1
**Reviewer**: Privacy Officer (to be designated)

**For Questions**:
- Privacy Officer: [TBD]
- Legal Counsel: [TBD]
- CAI Helpline: 1-888-528-7741
