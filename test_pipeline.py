import pandas as pd
import pytest

from pipeline import (
    clean_customers,
    clean_products,
    clean_orders,
    validate_customers,
    validate_products,
    validate_orders,
)


@pytest.fixture
def customers_data():
    return pd.DataFrame(
        {
            "customer_id": [101, 102, 102, None],
            "customer_name": [" Ada obi ", "BOB ADE", "Duplicate Bob", "Chris Doe"],
            "email": ["ADA@EXAMPLE.COM", "bob@example.com", "duplicate@example.com", "chris@example.com"],
            "city": [" lagos ", "Abuja", "Abuja", "Ibadan"],
        }
    )


@pytest.fixture
def products_data():
    return pd.DataFrame(
        {
            "product_id": [201, 202, 202, 203, 204],
            "product_name": [" rice ", "Chicken", "Duplicate Chicken", "Juice", "Invalid Product"],
            "category": [" food ", "Meal", "Meal", "Drinks", "Other"],
            "unit_price": [15000, 12000, 12000, 85000, -100],
        }
    )


@pytest.fixture
def orders_data():
    return pd.DataFrame(
        {
            "order_id": [5001, 5002, 5003, 5004, 5005, 5005],
            "customer_id": [101, 102, 999, 101, 101, 101],
            "product_id": [201, 202, 201, 999, 201, 201],
            "order_date": [
                "2026-09-01",
                "2026-09-02",
                "2026-09-03",
                "invalid-date",
                "2026-09-05",
                "2026-09-06",
            ],
            "quantity": [2, 1, 1, 1, -2, 1],
            "unit_price": [15000, 12000, 15000, 10000, 15000, 15000],
            "payment_status": [
                "paid",
                "PAID",
                "paid",
                "paid",
                "paid",
                "paid",
            ],
            "order_status": [
                "completed",
                "completed",
                "processing",
                "completed",
                "completed",
                "completed",
            ],
        }
    )


def test_clean_customers_standardises_text(customers_data):
    cleaned = clean_customers(customers_data)

    assert cleaned.loc[0, "customer_name"] == "Ada Obi"
    assert cleaned.loc[0, "email"] == "ada@example.com"
    assert cleaned.loc[0, "city"] == "Lagos"
    assert pd.api.types.is_numeric_dtype(cleaned["customer_id"])


def test_clean_products_removes_duplicate_product_ids(products_data):
    cleaned = clean_products(products_data)

    assert cleaned["product_id"].is_unique
    assert len(cleaned) == 4
    assert cleaned.loc[0, "product_name"] == "Rice"
    assert cleaned.loc[0, "category"] == "Food"


def test_clean_orders_converts_types_and_calculates_total(orders_data):
    cleaned = clean_orders(orders_data)

    assert pd.api.types.is_numeric_dtype(cleaned["order_id"])
    assert pd.api.types.is_numeric_dtype(cleaned["quantity"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["order_date"])
    assert cleaned.loc[0, "payment_status"] == "paid"
    assert cleaned.loc[0, "total_amount"] == 30000
    assert cleaned["order_id"].is_unique


def test_validate_customers_rejects_duplicate_and_missing_ids(customers_data):
    cleaned = clean_customers(customers_data)
    errors, valid = validate_customers(cleaned)

    assert len(errors) == 2
    assert len(valid) == 2
    assert "Duplicate customer ID" in errors.iloc[0]["error_reason"]
    assert "Missing customer ID" in errors.iloc[1]["error_reason"]
    assert "error_reason" in errors.columns


def test_validate_products_rejects_invalid_price(products_data):
    cleaned = clean_products(products_data)
    errors, valid = validate_products(cleaned)

    assert len(errors) == 1
    assert len(valid) == 3
    assert errors.iloc[0]["product_id"] == 204
    assert "Unit price" in errors.iloc[0]["error_reason"]


def test_validate_orders_rejects_unknown_customer_and_product(
    orders_data,
    customers_data,
    products_data,
):
    cleaned_orders = clean_orders(orders_data)
    valid_customers = clean_customers(customers_data).iloc[:2]
    valid_products = clean_products(products_data).iloc[:2]

    errors, valid = validate_orders(
        cleaned_orders,
        valid_customers,
        valid_products,
    )

    assert "Customer ID does not exist" in errors.iloc[0]["error_reason"]
    assert "Product ID does not exist" in errors.iloc[1]["error_reason"]
    assert len(valid) < len(cleaned_orders)


def test_validate_orders_rejects_invalid_date_and_quantity(
    orders_data,
    customers_data,
    products_data,
):
    cleaned_orders = clean_orders(orders_data)
    valid_customers = pd.DataFrame({"customer_id": [101, 102]})
    valid_products = pd.DataFrame({"product_id": [201, 202]})

    errors, _ = validate_orders(
        cleaned_orders,
        valid_customers,
        valid_products,
    )

    combined_reasons = " | ".join(errors["error_reason"].tolist())

    assert "Missing order date" in combined_reasons
    assert "Quantity less than or equal to 0" in combined_reasons


def test_valid_order_is_retained():
    orders = pd.DataFrame(
        {
            "order_id": [5001],
            "customer_id": [101],
            "product_id": [201],
            "order_date": pd.to_datetime(["2026-09-01"]),
            "quantity": [2],
            "unit_price": [15000],
            "payment_status": ["paid"],
            "order_status": ["completed"],
        }
    )
    customers = pd.DataFrame({"customer_id": [101]})
    products = pd.DataFrame({"product_id": [201]})

    errors, valid = validate_orders(orders, customers, products)

    assert errors.empty
    assert len(valid) == 1
    assert valid.iloc[0]["order_id"] == 5001
