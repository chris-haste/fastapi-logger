# Advanced Pattern Examples

**Security, tracing, enrichment, and specialized logging patterns**

This section covers advanced Fapilog patterns for production environments including security logging, PII redaction, trace propagation, and user context enrichment.

---

## 📚 What You'll Learn

- **Security Logging** - Audit trails and security event patterns
- **PII Redaction** - Automatic sensitive data protection
- **Trace Propagation** - Distributed tracing correlation
- **User Context** - Rich context enrichment patterns
- **Level-Aware Redaction** - Dynamic redaction based on log levels

---

## 🚀 Examples

### 16 - Security Logging

**Comprehensive security audit trails and compliance logging**

```python
#!/usr/bin/env python3
"""
Example 16: Security Logging

This example demonstrates security-focused logging patterns including
audit trails, authentication events, and compliance logging.
"""

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def setup_security_logging():
    """Configure logging for security events."""
    settings = LoggingSettings(
        level="INFO",
        json_console="json",  # JSON for log analysis
        queue_enabled=True,
        enable_resource_metrics=False,  # Disable for security compliance
    )
    configure_logging(settings=settings)


def log_authentication_event(user_id: str, success: bool, ip_address: str, user_agent: str):
    """Log authentication attempts."""
    if success:
        log.info("User authentication succeeded",
                 event_type="auth_success",
                 user_id=user_id,
                 source_ip=ip_address,
                 user_agent=user_agent,
                 compliance="PCI_DSS")
    else:
        log.warning("User authentication failed",
                    event_type="auth_failure",
                    user_id=user_id,
                    source_ip=ip_address,
                    user_agent=user_agent,
                    compliance="PCI_DSS",
                    security_alert=True)


def log_authorization_event(user_id: str, resource: str, action: str, granted: bool):
    """Log authorization decisions."""
    if granted:
        log.info("Authorization granted",
                 event_type="authz_granted",
                 user_id=user_id,
                 resource=resource,
                 action=action,
                 compliance="SOX")
    else:
        log.warning("Authorization denied",
                    event_type="authz_denied",
                    user_id=user_id,
                    resource=resource,
                    action=action,
                    compliance="SOX",
                    security_alert=True)


def log_data_access_event(user_id: str, data_type: str, operation: str, record_count: int):
    """Log data access for audit trails."""
    log.info("Data access event",
             event_type="data_access",
             user_id=user_id,
             data_type=data_type,
             operation=operation,
             record_count=record_count,
             compliance="GDPR",
             audit_trail=True)


def log_security_incident(incident_type: str, severity: str, details: dict):
    """Log security incidents."""
    log.error("Security incident detected",
              event_type="security_incident",
              incident_type=incident_type,
              severity=severity,
              **details,
              compliance="ISO_27001",
              requires_investigation=True)


def main():
    """Demonstrate security logging patterns."""
    setup_security_logging()

    print("=== Security Logging Example ===\n")

    # Authentication events
    log_authentication_event("user_123", True, "192.168.1.100", "Mozilla/5.0...")
    log_authentication_event("user_456", False, "10.0.0.5", "curl/7.68.0")

    # Authorization events
    log_authorization_event("user_123", "/admin/users", "read", True)
    log_authorization_event("user_456", "/admin/users", "delete", False)

    # Data access events
    log_data_access_event("user_123", "customer_data", "select", 25)
    log_data_access_event("user_789", "payment_info", "update", 1)

    # Security incidents
    log_security_incident("brute_force_attempt",
                         "high",
                         {"source_ip": "10.0.0.5",
                          "attempts": 15,
                          "time_window": "5_minutes"})

    print("Security events logged with compliance metadata")
    print("✅ Authentication tracking")
    print("✅ Authorization decisions")
    print("✅ Data access audit trails")
    print("✅ Security incident reporting")


if __name__ == "__main__":
    main()
```

**Key Features:**

- ✅ Compliance framework tagging
- ✅ Security event classification
- ✅ Audit trail preservation
- ✅ Incident severity tracking

---

### 17 - Trace Propagation

**Distributed tracing correlation across microservices**

```python
#!/usr/bin/env python3
"""
Example 17: Trace Propagation

This example demonstrates how to propagate trace IDs across service boundaries
for distributed tracing and request correlation.
"""

import asyncio
import uuid
from typing import Optional

from fapilog import configure_logging, log
from fapilog._internal.context import bind_context, get_context, clear_context


class TraceContext:
    """Manage trace context for distributed requests."""

    def __init__(self, trace_id: Optional[str] = None, span_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or str(uuid.uuid4())[:8]

    def create_child_span(self) -> "TraceContext":
        """Create a child span for sub-operations."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4())[:8]
        )

    def bind_to_logs(self):
        """Bind trace context to all subsequent logs."""
        bind_context(trace_id=self.trace_id, span_id=self.span_id)


async def service_a_handler(request_data: dict) -> dict:
    """Simulate service A handling a request."""
    # Create trace context for incoming request
    trace = TraceContext()
    trace.bind_to_logs()

    log.info("Service A: Request received",
             service="service_a",
             operation="handle_request",
             request_size=len(str(request_data)))

    # Simulate processing
    await asyncio.sleep(0.1)

    # Call service B
    response_b = await call_service_b(trace, request_data.get("user_id"))

    # Process response
    result = {
        "status": "success",
        "data": response_b,
        "processed_by": "service_a"
    }

    log.info("Service A: Request completed",
             service="service_a",
             operation="handle_request",
             response_size=len(str(result)))

    return result


async def call_service_b(parent_trace: TraceContext, user_id: str) -> dict:
    """Simulate calling service B with trace propagation."""
    # Create child span for service B call
    child_trace = parent_trace.create_child_span()
    child_trace.bind_to_logs()

    log.info("Service A: Calling service B",
             service="service_a",
             operation="call_service_b",
             target_service="service_b",
             user_id=user_id)

    # Simulate service B processing
    response = await service_b_handler(child_trace, user_id)

    log.info("Service A: Service B response received",
             service="service_a",
             operation="call_service_b",
             target_service="service_b",
             response_status=response.get("status"))

    return response


async def service_b_handler(trace: TraceContext, user_id: str) -> dict:
    """Simulate service B handling a request."""
    # Use received trace context
    trace.bind_to_logs()

    log.info("Service B: Request received",
             service="service_b",
             operation="handle_request",
             user_id=user_id)

    # Simulate database call
    await database_operation(trace, user_id)

    result = {
        "status": "success",
        "user_data": {"id": user_id, "name": f"User {user_id}"},
        "processed_by": "service_b"
    }

    log.info("Service B: Request completed",
             service="service_b",
             operation="handle_request",
             user_id=user_id)

    return result


async def database_operation(trace: TraceContext, user_id: str):
    """Simulate database operation with trace context."""
    # Create child span for database operation
    db_trace = trace.create_child_span()
    db_trace.bind_to_logs()

    log.info("Database: Query started",
             service="database",
             operation="select_user",
             user_id=user_id,
             query_type="select")

    # Simulate query execution
    await asyncio.sleep(0.05)

    log.info("Database: Query completed",
             service="database",
             operation="select_user",
             user_id=user_id,
             rows_returned=1,
             execution_time_ms=50)


async def main():
    """Demonstrate trace propagation across services."""
    configure_logging()

    print("=== Trace Propagation Example ===\n")

    # Simulate multiple concurrent requests
    requests = [
        {"user_id": "user_123", "action": "get_profile"},
        {"user_id": "user_456", "action": "update_settings"},
        {"user_id": "user_789", "action": "delete_account"}
    ]

    # Process requests concurrently
    tasks = [service_a_handler(req) for req in requests]
    results = await asyncio.gather(*tasks)

    print("\nTrace propagation completed!")
    print("✅ Trace IDs propagated across services")
    print("✅ Parent-child span relationships maintained")
    print("✅ All logs correlated by trace ID")
    print("✅ Service boundaries clearly defined")


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Features:**

- ✅ Automatic trace ID generation
- ✅ Parent-child span relationships
- ✅ Cross-service correlation
- ✅ Distributed request tracking

---

### 18 - User Context Enrichment

**Rich user context for personalized logging**

```python
#!/usr/bin/env python3
"""
Example 18: User Context Enrichment

This example demonstrates how to enrich logs with user context
including user details, permissions, and session information.
"""

from typing import Optional, Dict, Any
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context


class UserContext:
    """Rich user context for logging enrichment."""

    def __init__(self, user_id: str, email: str, role: str,
                 organization: str, session_id: str,
                 permissions: list = None, metadata: dict = None):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.organization = organization
        self.session_id = session_id
        self.permissions = permissions or []
        self.metadata = metadata or {}

    def bind_to_logs(self):
        """Bind user context to all subsequent logs."""
        context = {
            "user_id": self.user_id,
            "user_email": self.email,
            "user_role": self.role,
            "organization": self.organization,
            "session_id": self.session_id,
            "user_permissions": self.permissions,
            **self.metadata
        }
        bind_context(**context)

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions


def authenticate_user(token: str) -> Optional[UserContext]:
    """Simulate user authentication and context creation."""
    # Mock user database
    users = {
        "token_admin": UserContext(
            user_id="admin_001",
            email="admin@company.com",
            role="admin",
            organization="acme_corp",
            session_id="sess_123abc",
            permissions=["read", "write", "delete", "admin"],
            metadata={"department": "IT", "country": "US"}
        ),
        "token_user": UserContext(
            user_id="user_456",
            email="user@company.com",
            role="user",
            organization="acme_corp",
            session_id="sess_456def",
            permissions=["read", "write"],
            metadata={"department": "Sales", "country": "UK"}
        )
    }

    return users.get(token)


def admin_operation(user: UserContext, operation: str, target: str):
    """Perform admin operation with context logging."""
    user.bind_to_logs()

    if not user.has_permission("admin"):
        log.warning("Admin operation denied - insufficient permissions",
                    operation=operation,
                    target=target,
                    required_permission="admin")
        return False

    log.info("Admin operation started",
             operation=operation,
             target=target,
             admin_level="high")

    # Simulate operation
    if operation == "delete_user":
        log.warning("User deletion requested",
                    operation=operation,
                    target=target,
                    compliance="GDPR",
                    requires_approval=True)

    log.info("Admin operation completed",
             operation=operation,
             target=target,
             success=True)

    return True


def user_profile_update(user: UserContext, profile_data: dict):
    """Update user profile with context logging."""
    user.bind_to_logs()

    log.info("Profile update started",
             operation="update_profile",
             fields_updated=list(profile_data.keys()),
             field_count=len(profile_data))

    # Check for sensitive field updates
    sensitive_fields = {"email", "phone", "address"}
    updated_sensitive = set(profile_data.keys()) & sensitive_fields

    if updated_sensitive:
        log.info("Sensitive fields updated",
                 operation="update_profile",
                 sensitive_fields=list(updated_sensitive),
                 compliance="PII_PROTECTION")

    log.info("Profile update completed",
             operation="update_profile",
             success=True)


def data_access_operation(user: UserContext, resource: str, filters: dict):
    """Perform data access with context logging."""
    user.bind_to_logs()

    log.info("Data access requested",
             operation="data_access",
             resource=resource,
             filters=filters,
             filter_count=len(filters))

    # Log access patterns for analytics
    if user.metadata.get("department") == "Sales":
        log.info("Sales team data access",
                 operation="data_access",
                 resource=resource,
                 access_pattern="sales_reporting")

    # Simulate data filtering based on user context
    if user.role != "admin":
        log.info("Data filtered by user role",
                 operation="data_access",
                 resource=resource,
                 filtered_by="user_role",
                 role_restrictions=True)

    log.info("Data access completed",
             operation="data_access",
             resource=resource,
             records_returned=42)


def main():
    """Demonstrate user context enrichment."""
    configure_logging()

    print("=== User Context Enrichment Example ===\n")

    # Authenticate users
    admin_user = authenticate_user("token_admin")
    regular_user = authenticate_user("token_user")

    if admin_user:
        print("Admin user operations:")
        admin_operation(admin_user, "delete_user", "user_789")
        admin_operation(admin_user, "view_audit_logs", "all")

    if regular_user:
        print("\nRegular user operations:")
        user_profile_update(regular_user, {"phone": "+1-555-0123", "timezone": "UTC"})
        data_access_operation(regular_user, "sales_reports", {"year": 2024, "region": "UK"})

        # Try admin operation (should fail)
        admin_operation(regular_user, "delete_user", "user_789")

    print("\nUser context enrichment completed!")
    print("✅ Rich user context in all logs")
    print("✅ Permission-based operation logging")
    print("✅ Organizational context tracking")
    print("✅ Session correlation")


if __name__ == "__main__":
    main()
```

**Key Features:**

- ✅ Rich user context binding
- ✅ Permission-based logging
- ✅ Organizational metadata
- ✅ Session correlation

---

### 19 - Field Redaction

**Automatic PII and sensitive data protection**

```python
#!/usr/bin/env python3
"""
Example 19: Field Redaction

This example demonstrates automatic redaction of sensitive data
including PII, credentials, and custom sensitive patterns.
"""

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def setup_redaction_logging():
    """Configure logging with field redaction."""
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        # Enable automatic PII redaction
        redact_pii=True,
        # Custom redaction patterns
        redact_patterns=[
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit cards
            r'\b[A-Z]{2}\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{2}\b',  # IBANs
            r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+',  # Bearer tokens
            r'password["\s]*[:=]["\s]*[^"\s,}]+',  # Passwords in JSON/logs
        ],
        # Redaction replacement
        redaction_replacement="***REDACTED***"
    )
    configure_logging(settings=settings)


def log_user_registration(user_data: dict):
    """Log user registration with PII redaction."""
    log.info("User registration started",
             operation="user_registration",
             # These will be automatically redacted
             email=user_data.get("email"),
             phone=user_data.get("phone"),
             ssn=user_data.get("ssn"),
             credit_card=user_data.get("credit_card"),
             # Safe fields
             signup_source=user_data.get("source"),
             user_agent=user_data.get("user_agent")[:50])  # Truncated


def log_payment_processing(payment_data: dict):
    """Log payment processing with financial data redaction."""
    log.info("Payment processing started",
             operation="payment_processing",
             # Sensitive financial data (will be redacted)
             card_number=payment_data.get("card_number"),
             cvv=payment_data.get("cvv"),
             iban=payment_data.get("iban"),
             # Safe fields
             amount=payment_data.get("amount"),
             currency=payment_data.get("currency"),
             transaction_type=payment_data.get("type"))


def log_authentication_attempt(auth_data: dict):
    """Log authentication with credential redaction."""
    log.info("Authentication attempt",
             operation="authentication",
             username=auth_data.get("username"),
             # Password and tokens will be redacted
             password=auth_data.get("password"),
             access_token=auth_data.get("access_token"),
             refresh_token=auth_data.get("refresh_token"),
             # Safe fields
             client_ip=auth_data.get("client_ip"),
             user_agent=auth_data.get("user_agent"))


def log_api_request_with_sensitive_data(request_data: dict):
    """Log API request containing mixed sensitive/safe data."""
    log.info("API request received",
             operation="api_request",
             endpoint=request_data.get("endpoint"),
             method=request_data.get("method"),
             # Request body may contain sensitive data
             request_body=request_data.get("body"),
             # Headers may contain auth tokens
             authorization_header=request_data.get("headers", {}).get("Authorization"),
             # Safe fields
             content_type=request_data.get("headers", {}).get("Content-Type"),
             user_id=request_data.get("user_id"))


def demonstrate_custom_redaction():
    """Demonstrate custom redaction patterns."""
    log.info("Processing API key rotation",
             operation="key_rotation",
             # Custom patterns will be redacted
             old_api_key="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
             new_api_key="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODc2NTQzMjEwIn0",
             # Config with passwords will be redacted
             config='{"database": {"password": "secret123", "host": "db.company.com"}}')


def main():
    """Demonstrate field redaction capabilities."""
    setup_redaction_logging()

    print("=== Field Redaction Example ===\n")

    # User registration with PII
    user_data = {
        "email": "user@example.com",
        "phone": "+1-555-123-4567",
        "ssn": "123-45-6789",
        "credit_card": "4532 1234 5678 9012",
        "source": "mobile_app",
        "user_agent": "MyApp/1.0 (iOS 15.0)"
    }
    log_user_registration(user_data)

    # Payment processing
    payment_data = {
        "card_number": "4532-1234-5678-9012",
        "cvv": "123",
        "iban": "GB82 WEST 1234 5698 7654 32",
        "amount": 99.99,
        "currency": "USD",
        "type": "purchase"
    }
    log_payment_processing(payment_data)

    # Authentication
    auth_data = {
        "username": "john.doe@company.com",
        "password": "mySecretPassword123!",
        "access_token": "Bearer abc123def456ghi789",
        "refresh_token": "Bearer xyz987uvw654rst321",
        "client_ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    log_authentication_attempt(auth_data)

    # API request with mixed data
    request_data = {
        "endpoint": "/api/v1/users/profile",
        "method": "PATCH",
        "body": '{"email": "new@example.com", "phone": "+1-555-987-6543"}',
        "headers": {
            "Authorization": "Bearer secret_token_here",
            "Content-Type": "application/json"
        },
        "user_id": "user_123"
    }
    log_api_request_with_sensitive_data(request_data)

    # Custom redaction patterns
    demonstrate_custom_redaction()

    print("\nField redaction completed!")
    print("✅ PII automatically redacted")
    print("✅ Financial data protected")
    print("✅ Authentication credentials masked")
    print("✅ Custom patterns redacted")
    print("✅ Safe data preserved")


if __name__ == "__main__":
    main()
```

**Redaction Patterns:**

| Pattern          | Matches             | Example             |
| ---------------- | ------------------- | ------------------- |
| **Email**        | email@domain.com    | user@**_REDACTED_** |
| **Phone**        | +1-555-123-4567     | **_REDACTED_**      |
| **SSN**          | 123-45-6789         | **_REDACTED_**      |
| **Credit Card**  | 4532 1234 5678 9012 | **_REDACTED_**      |
| **Bearer Token** | Bearer abc123...    | **_REDACTED_**      |

**Key Features:**

- ✅ Automatic PII detection
- ✅ Custom redaction patterns
- ✅ Financial data protection
- ✅ Credential masking

---

### 20 - Automatic PII Redaction

**Advanced PII detection and protection**

```python
#!/usr/bin/env python3
"""
Example 20: Automatic PII Redaction

This example demonstrates advanced automatic PII detection
and redaction capabilities for compliance and privacy.
"""

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def setup_advanced_pii_protection():
    """Configure advanced PII protection."""
    settings = LoggingSettings(
        level="INFO",
        json_console="json",
        # Enable comprehensive PII redaction
        redact_pii=True,
        pii_redaction_level="strict",  # strict, moderate, basic
        # Custom PII patterns
        pii_patterns=[
            "medical_record_number",
            "passport_number",
            "driver_license",
            "bank_account_number"
        ],
        # Advanced redaction options
        redaction_preserve_length=True,  # ***REDACTED-8*** vs ***REDACTED***
        redaction_partial_reveal=True,   # Show first/last chars: j***@***.com
    )
    configure_logging(settings=settings)


def log_medical_data(patient_data: dict):
    """Log medical data with strict PII protection."""
    log.info("Patient record accessed",
             operation="medical_record_access",
             # Medical PII (will be redacted)
             patient_name=patient_data.get("name"),
             patient_ssn=patient_data.get("ssn"),
             medical_record_number=patient_data.get("mrn"),
             date_of_birth=patient_data.get("dob"),
             # Diagnosis codes (safe, not PII)
             diagnosis_codes=patient_data.get("diagnosis_codes"),
             procedure_codes=patient_data.get("procedure_codes"),
             # Provider info (may contain PII)
             physician_name=patient_data.get("physician"),
             facility_id=patient_data.get("facility_id"))


def log_financial_transaction(transaction_data: dict):
    """Log financial transaction with account protection."""
    log.info("Financial transaction processed",
             operation="financial_transaction",
             # Financial PII (will be redacted)
             account_number=transaction_data.get("account_number"),
             routing_number=transaction_data.get("routing_number"),
             cardholder_name=transaction_data.get("cardholder_name"),
             # Transaction details (safe)
             transaction_id=transaction_data.get("transaction_id"),
             amount=transaction_data.get("amount"),
             merchant_category=transaction_data.get("merchant_category"),
             transaction_type=transaction_data.get("type"))


def log_employment_data(employee_data: dict):
    """Log employment data with HR PII protection."""
    log.info("Employee record updated",
             operation="hr_record_update",
             # HR PII (will be redacted)
             employee_name=employee_data.get("name"),
             employee_ssn=employee_data.get("ssn"),
             home_address=employee_data.get("address"),
             personal_email=employee_data.get("personal_email"),
             emergency_contact=employee_data.get("emergency_contact"),
             # Work info (safe)
             employee_id=employee_data.get("employee_id"),
             department=employee_data.get("department"),
             job_title=employee_data.get("job_title"),
             start_date=employee_data.get("start_date"))


def demonstrate_redaction_levels():
    """Demonstrate different redaction levels."""

    # Basic data that would be redacted differently based on level
    sample_data = {
        "user_email": "john.smith@company.com",
        "phone": "+1-555-123-4567",
        "credit_card": "4532-1234-5678-9012"
    }

    log.info("Redaction level demonstration",
             operation="redaction_demo",
             redaction_level="strict",
             **sample_data)


def main():
    """Demonstrate automatic PII redaction."""
    setup_advanced_pii_protection()

    print("=== Automatic PII Redaction Example ===\n")

    # Medical data
    patient_data = {
        "name": "Jane Doe",
        "ssn": "987-65-4321",
        "mrn": "MRN-2024-001234",
        "dob": "1985-03-15",
        "diagnosis_codes": ["Z00.00", "I10"],
        "procedure_codes": ["99213"],
        "physician": "Dr. Sarah Johnson",
        "facility_id": "FAC-001"
    }
    log_medical_data(patient_data)

    # Financial data
    transaction_data = {
        "account_number": "123456789012",
        "routing_number": "021000021",
        "cardholder_name": "John Smith",
        "transaction_id": "TXN-789456123",
        "amount": 150.00,
        "merchant_category": "grocery",
        "type": "purchase"
    }
    log_financial_transaction(transaction_data)

    # Employment data
    employee_data = {
        "name": "Alice Johnson",
        "ssn": "456-78-9012",
        "address": "123 Main St, Anytown, ST 12345",
        "personal_email": "alice.j@personal.com",
        "emergency_contact": "Bob Johnson, +1-555-987-6543",
        "employee_id": "EMP-2024-567",
        "department": "Engineering",
        "job_title": "Senior Developer",
        "start_date": "2024-01-15"
    }
    log_employment_data(employee_data)

    # Redaction levels demo
    demonstrate_redaction_levels()

    print("\nAutomatic PII redaction completed!")
    print("✅ Medical data protected (HIPAA compliance)")
    print("✅ Financial data secured (PCI DSS compliance)")
    print("✅ HR data masked (employment privacy)")
    print("✅ Configurable redaction levels")
    print("✅ Preserved data structure for analysis")


if __name__ == "__main__":
    main()
```

**Redaction Levels:**

| Level        | Description         | Example                   |
| ------------ | ------------------- | ------------------------- |
| **Basic**    | Simple masking      | email → **_REDACTED_**    |
| **Moderate** | Length preservation | email → **_REDACTED-15_** |
| **Strict**   | Partial reveal      | email → j**_@_**.com      |

**Key Features:**

- ✅ Industry-specific PII patterns
- ✅ Configurable redaction levels
- ✅ Compliance framework support
- ✅ Structure preservation

---

## 🔒 Security & Compliance

### **GDPR Compliance**

```python
settings = LoggingSettings(
    redact_pii=True,
    pii_redaction_level="strict",
    compliance_mode="gdpr"
)
```

### **HIPAA Compliance**

```python
settings = LoggingSettings(
    redact_pii=True,
    pii_patterns=["medical_record_number", "patient_id"],
    compliance_mode="hipaa"
)
```

### **PCI DSS Compliance**

```python
settings = LoggingSettings(
    redact_pii=True,
    pii_patterns=["credit_card", "cardholder_data"],
    compliance_mode="pci_dss"
)
```

---

## 🎯 Next Steps

### 🚀 **Custom Components**

- **[Sink Development](../sinks/index.md)** - Build custom output destinations
- **[Advanced Development](../../advanced-development.md)** - Deep dive into Fapilog architecture

### 🏭 **Production Deployment**

- **[Production Examples](../production/index.md)** - High-performance configurations
- **[Configuration Guide](../../config.md)** - Complete configuration reference

### 📖 **Integration Patterns**

- **[FastAPI Examples](../fastapi/index.md)** - Web application patterns
- **[Basic Examples](../basic/index.md)** - Getting started patterns

---

## 💡 Advanced Tips

1. **Security First** - Always enable PII redaction in production
2. **Trace Everything** - Use trace propagation for distributed systems
3. **Enrich Context** - Add rich user context for better debugging
4. **Compliance Ready** - Configure for your regulatory requirements
5. **Monitor Access** - Log data access patterns for audit trails

Ready for custom sink development? Check out [sink examples](../sinks/index.md)!
