#!/usr/bin/env python3
"""
Example 8: FastAPI Structured Logging Patterns

This example demonstrates advanced structured logging patterns in FastAPI
applications, including performance monitoring, business metrics, and
comprehensive request/response logging with automatic request context
enrichment.

Note: As of fapilog with Story 6.1, request metadata (method, path,
status_code, client_ip, duration_ms, trace_id, etc.) is automatically
captured by TraceIDMiddleware. This example focuses on business-specific
structured logging.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel


# Pydantic models
class Product(BaseModel):
    id: int
    name: str
    price: float
    category: str
    in_stock: bool


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class Order(BaseModel):
    id: str
    customer_id: str
    items: List[OrderItem]
    total_amount: float
    status: str = "pending"


def create_app() -> FastAPI:
    """Create a FastAPI application with structured logging."""

    # Configure logging with automatic request context enrichment
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Pretty output for development
        queue_enabled=False,  # Disable queue for simpler example
    )

    # Configure logging - this automatically registers TraceIDMiddleware
    # which captures: method, path, status_code, client_ip, duration_ms,
    # trace_id, etc.
    configure_logging(settings=settings)

    # Create FastAPI app
    app = FastAPI(
        title="fapilog Structured Logging Example",
        description="Example showing advanced structured logging patterns "
        "with automatic request context",
        version="1.0.0",
    )

    # Log application startup
    log.info(
        "FastAPI application with structured logging starting",
        app_name="fapilog-structured-example",
        version="1.0.0",
        features=[
            "automatic_request_context",
            "business_metrics",
            "performance_monitoring",
        ],
    )

    return app


# Create the FastAPI application
app = create_app()


# Dependency for request timing (business-specific timing beyond automatic)
async def log_business_timing(request: Request):
    """Dependency to log business-specific timing."""
    start_time = time.perf_counter()
    request.state.business_start_time = start_time

    # Note: Basic request metadata (method, path, etc.) is automatically
    # logged. This dependency focuses on business-specific timing
    log.debug("Business timing started", operation="business_logic")
    return start_time


# Mock data store
products_db = {
    1: {
        "id": 1,
        "name": "Laptop",
        "price": 999.99,
        "category": "Electronics",
        "in_stock": True,
    },
    2: {
        "id": 2,
        "name": "Mouse",
        "price": 29.99,
        "category": "Electronics",
        "in_stock": True,
    },
    3: {
        "id": 3,
        "name": "Keyboard",
        "price": 79.99,
        "category": "Electronics",
        "in_stock": False,
    },
    4: {"id": 4, "name": "Book", "price": 19.99, "category": "Books", "in_stock": True},
}

orders_db = {}


@app.get("/")
async def root():
    """Root endpoint - request metadata automatically logged."""
    # Note: method, path, status_code, client_ip, duration_ms, trace_id
    # are automatically logged by TraceIDMiddleware
    log.info("Root endpoint accessed", service="structured-logging-example")
    return {"message": "Structured logging example API with automatic request context"}


@app.get("/products")
async def get_products(
    category: Optional[str] = None,
    in_stock_only: bool = False,
    timing: float = Depends(log_business_timing),
):
    """Get products with filtering and business metrics logging."""
    # Request metadata (method, path, etc.) automatically captured
    # Focus on business-specific logging
    log.info(
        "Products query started",
        operation="product_search",
        filters={"category": category, "in_stock_only": in_stock_only},
    )

    # Simulate database query
    await asyncio.sleep(0.1)

    # Apply filters
    filtered_products = []
    for product in products_db.values():
        if category and product["category"] != category:
            continue
        if in_stock_only and not product["in_stock"]:
            continue
        filtered_products.append(product)

    # Log business metrics (not request metadata - that's automatic)
    efficiency = len(filtered_products) / len(products_db) if products_db else 0
    log.info(
        "Products query completed",
        operation="product_search",
        metrics={
            "total_products": len(products_db),
            "filtered_count": len(filtered_products),
            "filter_efficiency": efficiency,
        },
        business_logic_ms=round((time.perf_counter() - timing) * 1000, 2),
    )

    return {
        "products": filtered_products,
        "total_count": len(filtered_products),
        "applied_filters": {"category": category, "in_stock_only": in_stock_only},
    }


@app.get("/products/{product_id}")
async def get_product(product_id: int):
    """Get specific product with detailed logging."""
    # Request context automatically captured
    log.info(
        "Product lookup started", operation="product_detail", product_id=product_id
    )

    if product_id not in products_db:
        log.warning(
            "Product not found",
            operation="product_detail",
            product_id=product_id,
            available_products=list(products_db.keys()),
        )
        raise HTTPException(status_code=404, detail="Product not found")

    product = products_db[product_id]

    # Log business metrics
    log.info(
        "Product retrieved successfully",
        operation="product_detail",
        product_id=product_id,
        product_category=product["category"],
        product_price=product["price"],
        in_stock=product["in_stock"],
    )

    return product


@app.post("/orders")
async def create_order(order_data: Dict[str, Any]):
    """Create order with comprehensive business logging."""
    order_id = str(uuid.uuid4())

    # Business logic logging (request metadata is automatic)
    log.info(
        "Order creation started",
        operation="order_create",
        order_id=order_id,
        customer_id=order_data.get("customer_id"),
        item_count=len(order_data.get("items", [])),
    )

    # Validate items and calculate total
    total_amount = 0
    order_items = []

    for item_data in order_data.get("items", []):
        product_id = item_data["product_id"]
        quantity = item_data["quantity"]

        if product_id not in products_db:
            log.error(
                "Invalid product in order",
                operation="order_create",
                order_id=order_id,
                invalid_product_id=product_id,
                customer_id=order_data.get("customer_id"),
            )
            raise HTTPException(
                status_code=400, detail=f"Product {product_id} not found"
            )

        product = products_db[product_id]

        if not product["in_stock"]:
            log.warning(
                "Out of stock product ordered",
                operation="order_create",
                order_id=order_id,
                product_id=product_id,
                product_name=product["name"],
                customer_id=order_data.get("customer_id"),
            )
            error_msg = f"Product {product['name']} is out of stock"
            raise HTTPException(status_code=400, detail=error_msg)

        item_total = product["price"] * quantity
        total_amount += item_total

        order_items.append(
            {
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": product["price"],
                "item_total": item_total,
            }
        )

    # Create order
    order = {
        "id": order_id,
        "customer_id": order_data["customer_id"],
        "items": order_items,
        "total_amount": total_amount,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }

    orders_db[order_id] = order

    # Log successful order creation with business metrics
    avg_item_value = total_amount / len(order_items) if order_items else 0
    log.info(
        "Order created successfully",
        operation="order_create",
        order_id=order_id,
        customer_id=order_data["customer_id"],
        metrics={
            "total_amount": total_amount,
            "item_count": len(order_items),
            "average_item_value": avg_item_value,
        },
        business_category="order_fulfillment",
    )

    return order


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details with audit logging."""
    # Request metadata automatically captured
    log.info("Order lookup started", operation="order_detail", order_id=order_id)

    if order_id not in orders_db:
        log.warning(
            "Order not found",
            operation="order_detail",
            order_id=order_id,
            available_orders=len(orders_db),
        )
        raise HTTPException(status_code=404, detail="Order not found")

    order = orders_db[order_id]

    # Audit logging for order access
    log.info(
        "Order accessed",
        operation="order_detail",
        order_id=order_id,
        customer_id=order["customer_id"],
        order_value=order["total_amount"],
        audit_category="data_access",
    )

    return order


@app.get("/analytics/orders")
async def get_order_analytics():
    """Get order analytics with business intelligence logging."""
    log.info("Order analytics requested", operation="analytics", report_type="orders")

    # Calculate analytics
    total_orders = len(orders_db)
    total_revenue = sum(order["total_amount"] for order in orders_db.values())
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Category breakdown
    category_sales = {}
    for order in orders_db.values():
        for item in order["items"]:
            product = products_db.get(item["product_id"])
            if product:
                category = product["category"]
                current_sales = category_sales.get(category, 0)
                category_sales[category] = current_sales + item["item_total"]

    analytics = {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "average_order_value": avg_order_value,
        "category_sales": category_sales,
        "generated_at": datetime.now().isoformat(),
    }

    # Business intelligence logging
    log.info(
        "Order analytics generated",
        operation="analytics",
        report_type="orders",
        metrics=analytics,
        business_category="business_intelligence",
    )

    return analytics


@app.get("/performance/slow")
async def slow_endpoint():
    """Slow endpoint for performance monitoring."""
    log.info("Slow operation started", operation="performance_test", test_type="slow")

    # Simulate slow operation
    await asyncio.sleep(2.0)

    log.info("Slow operation completed", operation="performance_test", test_type="slow")
    return {"message": "Slow operation completed", "duration": "2000ms"}


@app.get("/performance/fast")
async def fast_endpoint():
    """Fast endpoint for performance comparison."""
    log.info("Fast operation started", operation="performance_test", test_type="fast")

    # Simulate fast operation
    await asyncio.sleep(0.01)

    log.info("Fast operation completed", operation="performance_test", test_type="fast")
    return {"message": "Fast operation completed", "duration": "10ms"}


@app.get("/metrics/business")
async def get_business_metrics():
    """Generate business metrics with comprehensive logging."""
    log.info(
        "Business metrics calculation started",
        operation="metrics",
        metric_type="business",
    )

    # Calculate various business metrics
    in_stock_count = sum(1 for p in products_db.values() if p["in_stock"])
    out_of_stock_count = sum(1 for p in products_db.values() if not p["in_stock"])
    product_metrics = {
        "total_products": len(products_db),
        "in_stock_products": in_stock_count,
        "out_of_stock_products": out_of_stock_count,
        "categories": len({p["category"] for p in products_db.values()}),
    }

    total_revenue = sum(order["total_amount"] for order in orders_db.values())
    order_metrics = {
        "total_orders": len(orders_db),
        "total_revenue": total_revenue,
    }

    # Comprehensive business metrics logging
    log.info(
        "Business metrics calculated",
        operation="metrics",
        metric_type="business",
        product_metrics=product_metrics,
        order_metrics=order_metrics,
        business_category="key_performance_indicators",
    )

    return {
        "products": product_metrics,
        "orders": order_metrics,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    """Run the FastAPI application."""

    print("=== FastAPI Structured Logging Example (Updated for Story 6.1) ===")
    print("This example demonstrates:")
    print(
        "✅ Automatic request context enrichment (method, path, "
        "status_code, client_ip, duration_ms, trace_id)"
    )
    print(
        "✅ Business-specific structured logging (avoiding duplication "
        "with automatic context)"
    )
    print("✅ Performance monitoring and timing")
    print("✅ Business metrics and analytics")
    print("✅ Audit trails and tracking")
    print("✅ Business intelligence logging")
    print()
    print("Available endpoints:")
    print("  GET  /products              - List products with filtering")
    print("  GET  /products/{id}         - Get product details")
    print("  POST /orders                - Create order (comprehensive logging)")
    print("  GET  /orders/{id}           - Get order details")
    print("  GET  /analytics/orders      - Order analytics")
    print("  GET  /performance/slow      - Slow endpoint for timing")
    print("  GET  /performance/fast      - Fast endpoint for comparison")
    print("  GET  /metrics/business      - Business metrics")
    print()
    print("Key logging features:")
    print("✅ Automatic request metadata (via TraceIDMiddleware)")
    print("✅ Business metrics and KPIs")
    print("✅ Error tracking and debugging")
    print("✅ Audit trails for compliance")
    print("✅ Structured data for analysis")
    print()
    print(
        "Note: Request metadata (method, path, status_code, client_ip, "
        "duration_ms, trace_id)"
    )
    print("      is now automatically captured - no manual logging needed!")
    print()
    print(
        "Start the server with: uvicorn "
        "examples.08_fastapi_structured_logging:app --reload"
    )
    print("Then visit: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
