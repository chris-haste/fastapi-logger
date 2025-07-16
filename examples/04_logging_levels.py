#!/usr/bin/env python3
"""
Example 4: Logging Levels

This example demonstrates the different logging levels available in fapilog:
- DEBUG: Detailed information for debugging
- INFO: General information about program execution
- WARNING: Warning messages for potentially problematic situations
- ERROR: Error messages for serious problems
- CRITICAL: Critical errors that may prevent the program from running
"""

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def demonstrate_debug_level():
    """Show DEBUG level logging."""
    print("=== DEBUG Level Logging ===")
    print("Shows: All messages (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    print("-" * 50)

    settings = LoggingSettings(
        level="DEBUG",
        json_console="pretty",  # Use pretty for readability
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # All levels will be shown
    log.debug(
        "Debug: Detailed debugging information",
        debug_data="internal state",
        function="process_user_data",
        step="validation",
    )

    log.info("Info: General information", user_id="user_123", action="login")

    log.warning(
        "Warning: Potentially problematic situation",
        endpoint="/api/users",
        rate_limit=95,
    )

    log.error(
        "Error: Serious problem occurred",
        database="postgres",
        error="connection timeout",
    )

    log.critical(
        "Critical: Critical error that may prevent operation",
        component="database",
        error="all connections failed",
    )


def demonstrate_info_level():
    """Show INFO level logging (default)."""
    print("\n\n=== INFO Level Logging (Default) ===")
    print("Shows: INFO, WARNING, ERROR, CRITICAL (hides DEBUG)")
    print("-" * 50)

    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # DEBUG will be hidden, others will show
    log.debug("Debug: This will be hidden", hidden=True)
    log.info("Info: This will be shown", visible=True)
    log.warning("Warning: This will be shown", visible=True)
    log.error("Error: This will be shown", visible=True)
    log.critical("Critical: This will be shown", visible=True)


def demonstrate_warning_level():
    """Show WARNING level logging."""
    print("\n\n=== WARNING Level Logging ===")
    print("Shows: WARNING, ERROR, CRITICAL (hides DEBUG, INFO)")
    print("-" * 50)

    settings = LoggingSettings(
        level="WARNING",
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # DEBUG and INFO will be hidden
    log.debug("Debug: This will be hidden", hidden=True)
    log.info("Info: This will be hidden", hidden=True)
    log.warning("Warning: This will be shown", visible=True)
    log.error("Error: This will be shown", visible=True)
    log.critical("Critical: This will be shown", visible=True)


def demonstrate_error_level():
    """Show ERROR level logging."""
    print("\n\n=== ERROR Level Logging ===")
    print("Shows: ERROR, CRITICAL (hides DEBUG, INFO, WARNING)")
    print("-" * 50)

    settings = LoggingSettings(
        level="ERROR",
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # Only ERROR and CRITICAL will show
    log.debug("Debug: This will be hidden", hidden=True)
    log.info("Info: This will be hidden", hidden=True)
    log.warning("Warning: This will be hidden", hidden=True)
    log.error("Error: This will be shown", visible=True)
    log.critical("Critical: This will be shown", visible=True)


def demonstrate_critical_level():
    """Show CRITICAL level logging."""
    print("\n\n=== CRITICAL Level Logging ===")
    print("Shows: Only CRITICAL (hides all others)")
    print("-" * 50)

    settings = LoggingSettings(
        level="CRITICAL",
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # Only CRITICAL will show
    log.debug("Debug: This will be hidden", hidden=True)
    log.info("Info: This will be hidden", hidden=True)
    log.warning("Warning: This will be hidden", hidden=True)
    log.error("Error: This will be hidden", hidden=True)
    log.critical("Critical: Only this will be shown", visible=True)


def demonstrate_practical_examples():
    """Show practical examples of when to use each level."""
    print("\n\n=== Practical Examples ===")
    print("Real-world scenarios for each logging level")
    print("-" * 50)

    settings = LoggingSettings(
        level="DEBUG",  # Show all levels for this example
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # DEBUG examples
    log.debug(
        "Function entry",
        function="process_payment",
        parameters={"amount": 100, "currency": "USD"},
    )

    log.debug(
        "Database query executed",
        query="SELECT * FROM users WHERE id = ?",
        parameters=[123],
        execution_time_ms=5.2,
    )

    # INFO examples
    log.info(
        "User action completed",
        user_id="user_456",
        action="purchase",
        amount=99.99,
        currency="USD",
    )

    log.info("Service started", service="payment_processor", version="1.2.3", port=8080)

    # WARNING examples
    log.warning(
        "Rate limit approaching",
        endpoint="/api/payments",
        current_requests=95,
        limit=100,
    )

    log.warning(
        "Deprecated API used",
        endpoint="/api/v1/users",
        replacement="/api/v2/users",
        sunset_date="2024-12-31",
    )

    # ERROR examples
    log.error(
        "Database connection failed",
        database="postgres",
        host="db.example.com",
        error="connection timeout",
        retry_count=3,
    )

    log.error(
        "Payment processing failed",
        payment_id="pay_123",
        error="insufficient_funds",
        user_id="user_789",
    )

    # CRITICAL examples
    log.critical(
        "All database connections failed",
        database="postgres",
        error="connection pool exhausted",
        impact="service unavailable",
    )

    log.critical(
        "Application startup failed",
        error="configuration invalid",
        missing_vars=["DATABASE_URL", "API_KEY"],
    )


def demonstrate_level_comparison():
    """Show a comparison of all levels side by side."""
    print("\n\n=== Logging Level Comparison ===")
    print("Summary of what each level shows:")
    print("-" * 50)

    levels = [
        ("DEBUG", "All messages"),
        ("INFO", "INFO, WARNING, ERROR, CRITICAL"),
        ("WARNING", "WARNING, ERROR, CRITICAL"),
        ("ERROR", "ERROR, CRITICAL"),
        ("CRITICAL", "CRITICAL only"),
    ]

    for level, description in levels:
        print(f"{level:8} → {description}")

    print("\nRecommended usage:")
    print("DEBUG    → Development, troubleshooting")
    print("INFO     → Production (default)")
    print("WARNING  → Production with reduced noise")
    print("ERROR    → Error monitoring only")
    print("CRITICAL → Emergency situations only")


def main():
    """Run all logging level examples."""
    demonstrate_debug_level()
    demonstrate_info_level()
    demonstrate_warning_level()
    demonstrate_error_level()
    demonstrate_critical_level()
    demonstrate_practical_examples()
    demonstrate_level_comparison()

    print("\n" + "=" * 60)
    print("Logging Level Summary:")
    print("✅ DEBUG: Detailed debugging information")
    print("✅ INFO: General information (default)")
    print("✅ WARNING: Potentially problematic situations")
    print("✅ ERROR: Serious problems")
    print("✅ CRITICAL: Critical errors that may prevent operation")
    print("✅ Levels are hierarchical (higher levels include lower)")
    print("✅ Use appropriate level for your use case")


if __name__ == "__main__":
    main()
