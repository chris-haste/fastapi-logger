#!/usr/bin/env python3
"""
Example 8: FastAPI Structured Logging Patterns

This example demonstrates advanced structured logging patterns in FastAPI
applications, including performance monitoring, business metrics, and
comprehensive request/response logging.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


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


class Order(BaseModel):
    customer_id: int
    items: List[OrderItem]
    shipping_address: str


class OrderResponse(BaseModel):
    order_id: str
    customer_id: int
    total_amount: float
    status: str
    created_at: datetime


def create_app() -> FastAPI:
    """Create a FastAPI application with structured logging patterns."""

    # Configure logging
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=False,
    )

    configure_logging(settings=settings)

    # Create FastAPI app
    app = FastAPI(
        title="fapilog Structured Logging Example",
        description="Example showing advanced structured logging patterns",
        version="1.0.0",
    )

    log.info(
        "FastAPI application with structured logging starting",
        app_name="fapilog-structured-logging-example",
        version="1.0.0",
        features=["performance_monitoring", "business_metrics", "request_tracking"],
    )

    return app


# Create the FastAPI application
app = create_app()


# Dependency for request timing
async def log_request_timing(request: Request):
    """Dependency to log request timing and metadata."""
    start_time = time.perf_counter()

    # Log request start
    log.info(
        "Request started",
        endpoint=str(request.url.path),
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
    )

    # Store timing info in request state
    request.state.start_time = start_time

    return start_time


# Dependency for response logging
async def log_response_timing(request: Request, response: Response):
    """Dependency to log response timing and metadata."""
    if hasattr(request.state, "start_time"):
        duration = time.perf_counter() - request.state.start_time
        duration_ms = round(duration * 1000, 2)

        log.info(
            "Request completed",
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            response_size=len(str(response.body)) if hasattr(response, "body") else 0,
        )


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
    """Root endpoint with basic structured logging."""
    log.info(
        "Root endpoint accessed",
        endpoint="/",
        method="GET",
        timestamp=datetime.now().isoformat(),
    )

    return {"message": "Structured logging example API"}


@app.get("/products")
async def get_products(
    category: Optional[str] = None,
    in_stock_only: bool = False,
    timing: float = Depends(log_request_timing),
):
    """Get products with filtering and performance logging."""
    log.info(
        "Products request started",
        endpoint="/products",
        method="GET",
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

    # Log performance metrics
    log.info(
        "Products retrieved successfully",
        endpoint="/products",
        method="GET",
        total_products=len(products_db),
        filtered_count=len(filtered_products),
        filters_applied={
            "category_filter": category is not None,
            "stock_filter": in_stock_only,
        },
    )

    return {"products": filtered_products}


@app.get("/products/{product_id}")
async def get_product(product_id: int, timing: float = Depends(log_request_timing)):
    """Get specific product with detailed logging."""
    log.info(
        "Product detail requested",
        endpoint=f"/products/{product_id}",
        method="GET",
        product_id=product_id,
    )

    # Simulate database lookup
    await asyncio.sleep(0.05)

    if product_id not in products_db:
        log.warning(
            "Product not found",
            endpoint=f"/products/{product_id}",
            method="GET",
            product_id=product_id,
            available_ids=list(products_db.keys()),
        )
        raise HTTPException(status_code=404, detail="Product not found")

    product = products_db[product_id]

    log.info(
        "Product retrieved successfully",
        endpoint=f"/products/{product_id}",
        method="GET",
        product_id=product_id,
        product_name=product["name"],
        product_price=product["price"],
        product_category=product["category"],
        in_stock=product["in_stock"],
    )

    return product


@app.post("/orders")
async def create_order(order: Order, timing: float = Depends(log_request_timing)):
    """Create order with comprehensive business logging."""
    order_id = str(uuid.uuid4())

    log.info(
        "Order creation started",
        endpoint="/orders",
        method="POST",
        order_id=order_id,
        customer_id=order.customer_id,
        item_count=len(order.items),
        shipping_address=order.shipping_address,
    )

    # Validate products and calculate total
    total_amount = 0.0
    order_items = []

    for item in order.items:
        if item.product_id not in products_db:
            log.error(
                "Invalid product in order",
                order_id=order_id,
                product_id=item.product_id,
                available_products=list(products_db.keys()),
            )
            raise HTTPException(
                status_code=400, detail=f"Product {item.product_id} not found"
            )

        product = products_db[item.product_id]

        if not product["in_stock"]:
            log.warning(
                "Out of stock product in order",
                order_id=order_id,
                product_id=item.product_id,
                product_name=product["name"],
                requested_quantity=item.quantity,
            )
            raise HTTPException(
                status_code=400, detail=f"Product {product['name']} is out of stock"
            )

        item_total = product["price"] * item.quantity
        total_amount += item_total

        order_items.append(
            {
                "product_id": item.product_id,
                "product_name": product["name"],
                "quantity": item.quantity,
                "unit_price": product["price"],
                "item_total": item_total,
            }
        )

    # Simulate order processing
    await asyncio.sleep(0.2)

    # Create order response
    order_response = OrderResponse(
        order_id=order_id,
        customer_id=order.customer_id,
        total_amount=total_amount,
        status="confirmed",
        created_at=datetime.now(),
    )

    # Store order
    orders_db[order_id] = {
        "order": order.dict(),
        "response": order_response.dict(),
        "items": order_items,
    }

    # Log business metrics
    log.info(
        "Order created successfully",
        endpoint="/orders",
        method="POST",
        order_id=order_id,
        customer_id=order.customer_id,
        total_amount=total_amount,
        item_count=len(order.items),
        business_metrics={
            "order_value": total_amount,
            "items_ordered": len(order.items),
            "unique_products": len(set(item.product_id for item in order.items)),
        },
    )

    return order_response


@app.get("/orders/{order_id}")
async def get_order(order_id: str, timing: float = Depends(log_request_timing)):
    """Get order details with audit logging."""
    log.info(
        "Order details requested",
        endpoint=f"/orders/{order_id}",
        method="GET",
        order_id=order_id,
    )

    # Simulate database lookup
    await asyncio.sleep(0.05)

    if order_id not in orders_db:
        log.warning(
            "Order not found",
            endpoint=f"/orders/{order_id}",
            method="GET",
            order_id=order_id,
            total_orders=len(orders_db),
        )
        raise HTTPException(status_code=404, detail="Order not found")

    order_data = orders_db[order_id]

    log.info(
        "Order retrieved successfully",
        endpoint=f"/orders/{order_id}",
        method="GET",
        order_id=order_id,
        customer_id=order_data["response"]["customer_id"],
        total_amount=order_data["response"]["total_amount"],
        status=order_data["response"]["status"],
        created_at=order_data["response"]["created_at"],
    )

    return order_data["response"]


@app.get("/analytics/orders")
async def get_order_analytics():
    """Get order analytics with business intelligence logging."""
    log.info("Order analytics requested", endpoint="/analytics/orders", method="GET")

    # Calculate analytics
    total_orders = len(orders_db)
    total_revenue = sum(
        order["response"]["total_amount"] for order in orders_db.values()
    )
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Product popularity
    product_counts = {}
    for order in orders_db.values():
        for item in order["items"]:
            product_id = item["product_id"]
            product_counts[product_id] = (
                product_counts.get(product_id, 0) + item["quantity"]
            )

    most_popular_product = (
        max(product_counts.items(), key=lambda x: x[1]) if product_counts else None
    )

    # Log business intelligence
    log.info(
        "Order analytics calculated",
        endpoint="/analytics/orders",
        method="GET",
        analytics={
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_order_value": avg_order_value,
            "most_popular_product_id": (
                most_popular_product[0] if most_popular_product else None
            ),
            "most_popular_product_quantity": (
                most_popular_product[1] if most_popular_product else 0
            ),
        },
        business_insights={
            "revenue_per_order": avg_order_value,
            "total_products_ordered": sum(product_counts.values()),
            "unique_products_ordered": len(product_counts),
        },
    )

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
        "most_popular_product": most_popular_product,
    }


@app.get("/performance/slow")
async def slow_endpoint():
    """Slow endpoint to demonstrate performance monitoring."""
    log.info("Slow endpoint started", endpoint="/performance/slow", method="GET")

    # Simulate slow operation
    await asyncio.sleep(3)

    log.info(
        "Slow endpoint completed",
        endpoint="/performance/slow",
        method="GET",
        duration_seconds=3,
    )

    return {"message": "Slow operation completed"}


@app.get("/performance/fast")
async def fast_endpoint():
    """Fast endpoint for comparison."""
    log.info("Fast endpoint accessed", endpoint="/performance/fast", method="GET")

    return {"message": "Fast operation completed"}


@app.get("/metrics/business")
async def business_metrics():
    """Business metrics endpoint with comprehensive logging."""
    log.info("Business metrics requested", endpoint="/metrics/business", method="GET")

    # Calculate various business metrics
    total_products = len(products_db)
    in_stock_products = sum(1 for p in products_db.values() if p["in_stock"])
    total_orders = len(orders_db)
    total_revenue = sum(
        order["response"]["total_amount"] for order in orders_db.values()
    )

    # Category breakdown
    category_revenue = {}
    for order in orders_db.values():
        for item in order["items"]:
            product = products_db[item["product_id"]]
            category = product["category"]
            revenue = item["item_total"]
            category_revenue[category] = category_revenue.get(category, 0) + revenue

    log.info(
        "Business metrics calculated",
        endpoint="/metrics/business",
        method="GET",
        metrics={
            "total_products": total_products,
            "in_stock_products": in_stock_products,
            "stock_ratio": (
                in_stock_products / total_products if total_products > 0 else 0
            ),
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_order_value": total_revenue / total_orders if total_orders > 0 else 0,
            "category_revenue": category_revenue,
        },
    )

    return {
        "total_products": total_products,
        "in_stock_products": in_stock_products,
        "stock_ratio": in_stock_products / total_products if total_products > 0 else 0,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_order_value": total_revenue / total_orders if total_orders > 0 else 0,
        "category_revenue": category_revenue,
    }


# Middleware for response logging
@app.middleware("http")
async def response_logging_middleware(request: Request, call_next):
    """Middleware to log response timing and metadata."""
    start_time = time.perf_counter()

    # Process the request
    response = await call_next(request)

    # Calculate timing
    duration = time.perf_counter() - start_time
    duration_ms = round(duration * 1000, 2)

    # Log response metrics
    log.info(
        "Response metrics",
        endpoint=str(request.url.path),
        method=request.method,
        status_code=response.status_code,
        duration_ms=duration_ms,
        response_size=len(str(response.body)) if hasattr(response, "body") else 0,
        performance_category=(
            "slow" if duration_ms > 1000 else "fast" if duration_ms < 100 else "normal"
        ),
    )

    return response


def main():
    """Run the FastAPI application."""
    import uvicorn

    print("=== FastAPI Structured Logging Example ===")
    print("This example demonstrates:")
    print("✅ Performance monitoring and timing")
    print("✅ Business metrics and analytics")
    print("✅ Comprehensive request/response logging")
    print("✅ Audit trails and tracking")
    print("✅ Business intelligence logging")
    print("✅ Structured data in all logs")
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
    print("✅ Request timing and performance metrics")
    print("✅ Business metrics and KPIs")
    print("✅ Error tracking and debugging")
    print("✅ Audit trails for compliance")
    print("✅ Structured data for analysis")
    print()
    print(
        "Start the server with: uvicorn examples.08_fastapi_structured_logging:app --reload"
    )
    print("Then visit: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
