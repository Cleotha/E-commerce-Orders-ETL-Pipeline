
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
    return pd.DataFrame({
        "customer_id": [101, 102, 102, None],
        "customer_name": [
            " Ada obi ",
            "BOB ADE",
            "Duplicate Bob",
            "Chris Doe",
        ],
        "email": [
            "ADA@EXAMPLE.COM",
            "bob@example.com",
            "duplicate@example.com",
            "chris@example.com",
        ],
        "city": [" lagos ", "Abuja", "Abuja", "Ibadan"],
    })


@pytest.fixture
def products_data():
    return pd.DataFrame({
        "product_id": [201, 202, 202, 203, 204],
        "product_name": [
            " rice ",
            "Chicken",
            "Duplicate Chicken",
            "Juice",
            "Invalid Product",
        ],
        "category": [" food ", "Meal", "Meal", "Drinks", "Other"],
        "unit_price": [15000, 12000, 12000, 85000, -100],
    })


@pytest.fixture
def orders_data():
    return pd.DataFrame({
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
            "paid", "PAID", "paid", "paid", "paid", "paid"
        ],
        "order_status": [
            "completed", "completed", "processing",
            "completed", "completed", "completed"
        ],
    })



def test_clean_customers_standardizes_text(customers_data):
    cleaned = clean_customers(customers_data)

    assert cleaned.loc[0, "customer_name"] == "Ada Obi"
    assert cleaned.loc[0, "email"] == "ada@example.com"
    assert cleaned.loc[0, "city"] == "Lagos"


def test_clean_customers_converts_customer_id_to_numeric(customers_data):
    cleaned = clean_customers(customers_data)

    assert pd.api.types.is_numeric_dtype(cleaned["customer_id"])
    assert pd.isna(cleaned.loc[3, "customer_id"])



def test_clean_products_standardizes_text(products_data):
    cleaned = clean_products(products_data)

    assert cleaned.loc[0, "product_name"] == "Rice"
    assert cleaned.loc[0, "category"] == "Food"


def test_clean_products_converts_numeric_columns(products_data):
    cleaned = clean_products(products_data)

    assert pd.api.types.is_numeric_dtype(cleaned["product_id"])
    assert pd.api.types.is_numeric_dtype(cleaned["unit_price"])


def test_clean_products_does_not_silently_drop_duplicates(products_data):
    cleaned = clean_products(products_data)

    # Duplicate handling belongs to the validation stage.
    assert len(cleaned) == len(products_data)
    assert cleaned["product_id"].duplicated().sum() == 1


def test_clean_orders_converts_dates_and_numeric_values(orders_data):
    cleaned = clean_orders(orders_data)

    assert pd.api.types.is_numeric_dtype(cleaned["order_id"])
    assert pd.api.types.is_numeric_dtype(cleaned["quantity"])
    assert pd.api.types.is_numeric_dtype(cleaned["unit_price"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["order_date"])


def test_clean_orders_normalizes_statuses(orders_data):
    cleaned = clean_orders(orders_data)

    assert cleaned.loc[1, "payment_status"] == "paid"
    assert cleaned.loc[0, "order_status"] == "completed"


def test_clean_orders_preserves_duplicate_ids_for_validation(orders_data):
    cleaned = clean_orders(orders_data)

    assert len(cleaned) == len(orders_data)
    assert cleaned["order_id"].duplicated().sum() == 1



def test_validate_customers_rejects_duplicate_and_missing_ids(
    customers_data,
):
    cleaned = clean_customers(customers_data)
    errors, valid = validate_customers(cleaned)

    assert len(errors) == 2
    assert len(valid) == 2
    assert "error_reason" in errors.columns

    duplicate_error = errors.loc[
        errors["customer_name"] == "Duplicate Bob",
        "error_reason",
    ].iloc[0]

    missing_id_error = errors.loc[
        errors["customer_name"] == "Chris Doe",
        "error_reason",
    ].iloc[0]

    assert "Duplicate customer ID" in duplicate_error
    assert "Missing customer ID" in missing_id_error


def test_validate_customers_rejects_missing_required_fields():
    customers = pd.DataFrame({
        "customer_id": [101, 102],
        "customer_name": ["Ada", None],
        "email": ["ada@example.com", "bob@example.com"],
        "city": ["Lagos", None],
    })

    errors, valid = validate_customers(customers)

    assert len(errors) == 1
    assert len(valid) == 1
    assert "Missing customer name" in errors.iloc[0]["error_reason"]
    assert "Missing city" in errors.iloc[0]["error_reason"]



def test_validate_products_rejects_duplicate_ids_and_invalid_prices(
    products_data,
):
    cleaned = clean_products(products_data)
    errors, valid = validate_products(cleaned)

    assert len(errors) == 2
    assert len(valid) == 3

    duplicate_error = errors.loc[
        errors["product_id"] == 202,
        "error_reason",
    ].iloc[0]

    price_error = errors.loc[
        errors["product_id"] == 204,
        "error_reason",
    ].iloc[0]

    assert "Duplicate product ID" in duplicate_error
    assert "Unit price" in price_error


def test_validate_products_rejects_missing_product_fields():
    products = pd.DataFrame({
        "product_id": [201],
        "product_name": [None],
        "category": ["Food"],
        "unit_price": [1000],
    })

    errors, valid = validate_products(products)

    assert len(errors) == 1
    assert valid.empty
    assert "Missing product name" in errors.iloc[0]["error_reason"]



@pytest.fixture
def validated_parent_data(customers_data, products_data):
    cleaned_customers = clean_customers(customers_data)
    customer_errors, valid_customers = validate_customers(cleaned_customers)

    cleaned_products = clean_products(products_data)
    product_errors, valid_products = validate_products(cleaned_products)

    return valid_customers, valid_products


def test_validate_orders_rejects_unknown_foreign_keys(
    orders_data,
    validated_parent_data,
):
    valid_customers, valid_products = validated_parent_data
    cleaned_orders = clean_orders(orders_data)

    errors, _ = validate_orders(
        cleaned_orders,
        valid_customers,
        valid_products,
    )

    unknown_customer = errors.loc[
        errors["order_id"] == 5003,
        "error_reason",
    ].iloc[0]

    unknown_product = errors.loc[
        errors["order_id"] == 5004,
        "error_reason",
    ].iloc[0]

    assert "Customer ID does not exist" in unknown_customer
    assert "Product ID does not exist" in unknown_product


def test_validate_orders_rejects_invalid_dates_and_quantities(
    orders_data,
    validated_parent_data,
):
    valid_customers, valid_products = validated_parent_data
    cleaned_orders = clean_orders(orders_data)

    errors, _ = validate_orders(
        cleaned_orders,
        valid_customers,
        valid_products,
    )

    invalid_date_error = errors.loc[
        errors["order_id"] == 5004,
        "error_reason",
    ].iloc[0]

    invalid_quantity_error = errors.loc[
        (errors["order_id"] == 5005)
        & (errors["quantity"] == -2),
        "error_reason",
    ].iloc[0]

    assert "Missing order date" in invalid_date_error
    assert "Quantity less than or equal to 0" in invalid_quantity_error


def test_validate_orders_rejects_duplicate_order_ids(
    orders_data,
    validated_parent_data,
):
    valid_customers, valid_products = validated_parent_data
    cleaned_orders = clean_orders(orders_data)

    errors, _ = validate_orders(
        cleaned_orders,
        valid_customers,
        valid_products,
    )

    duplicate_rows = errors.loc[errors["order_id"] == 5005]

    assert len(duplicate_rows) == 2
    assert any(
        "Duplicate order ID" in reason
        for reason in duplicate_rows["error_reason"]
    )


def test_validate_orders_rejects_invalid_statuses(
    validated_parent_data,
):
    valid_customers, valid_products = validated_parent_data

    orders = pd.DataFrame({
        "order_id": [6001, 6002],
        "customer_id": [101, 101],
        "product_id": [201, 201],
        "order_date": pd.to_datetime(["2026-09-01", "2026-09-02"]),
        "quantity": [1, 1],
        "unit_price": [15000, 15000],
        "payment_status": ["unknown", "paid"],
        "order_status": ["completed", "unknown"],
    })

    errors, valid = validate_orders(
        orders,
        valid_customers,
        valid_products,
    )

    assert len(errors) == 2
    assert valid.empty
    assert "Invalid payment status" in errors.iloc[0]["error_reason"]
    assert "Invalid order status" in errors.iloc[1]["error_reason"]


def test_validate_orders_retains_a_valid_order():
    orders = pd.DataFrame({
        "order_id": [7001],
        "customer_id": [101],
        "product_id": [201],
        "order_date": pd.to_datetime(["2026-09-01"]),
        "quantity": [2],
        "unit_price": [15000],
        "payment_status": ["paid"],
        "order_status": ["completed"],
    })

    customers = pd.DataFrame({"customer_id": [101]})
    products = pd.DataFrame({"product_id": [201]})

    errors, valid = validate_orders(orders, customers, products)

    assert errors.empty
    assert len(valid) == 1
    assert valid.iloc[0]["order_id"] == 7001


def test_validate_orders_records_multiple_reasons_for_one_row():
    orders = pd.DataFrame({
        "order_id": [7002],
        "customer_id": [999],
        "product_id": [999],
        "order_date": pd.to_datetime([None]),
        "quantity": [-1],
        "unit_price": [-100],
        "payment_status": ["unknown"],
        "order_status": ["unknown"],
    })

    customers = pd.DataFrame({"customer_id": [101]})
    products = pd.DataFrame({"product_id": [201]})

    errors, valid = validate_orders(orders, customers, products)

    assert len(errors) == 1
    assert valid.empty

    reason = errors.iloc[0]["error_reason"]

    assert "Customer ID does not exist" in reason
    assert "Product ID does not exist" in reason
    assert "Missing order date" in reason
    assert "Quantity less than or equal to 0" in reason
    assert "Unit_price less than 0" in reason
    assert "Invalid payment status" in reason
    assert "Invalid order status" in reason
