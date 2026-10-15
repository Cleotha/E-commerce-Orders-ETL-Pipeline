# E-commerce Orders ETL Pipeline

A Python and PostgreSQL data pipeline that extracts customer, product, and order data, cleans and validates the records, saves rejected records for inspection, and loads valid data into a relational database.

## Project objective

The purpose of this project is to demonstrate a complete junior-level data engineering workflow:

```text
Extract → Transform → Validate → Save errors → Load to PostgreSQL → Analyse with SQL
```

The pipeline protects the database from invalid records while keeping rejected data available for review.

## Technologies used

- Python
- Jupyter Notebook / Python scripts
- Pandas
- PostgreSQL
- SQLAlchemy
- Psycopg
- Pytest
- Python `logging`
- CSV and JSON files
- Git and GitHub

## Data sources

The pipeline processes three datasets:

```text
customers.csv
products.json
orders.csv
```

The order data contains fields such as:

```text
order_id
customer_id
product_id
order_date
quantity
unit_price
payment_status
order_status
```

## Pipeline workflow

### 1. Extract

The Python pipeline reads the raw customer, product, and order files using Pandas. It logs the number of records extracted from each source.

### 2. Clean and transform

The pipeline:

- replaces empty strings with missing values;
- converts IDs and numeric fields to numeric types;
- converts order dates to datetime values;
- standardises customer names and cities;
- converts emails to lowercase;
- standardises payment and order statuses to lowercase;
- removes duplicate product and order IDs according to the project rules;
- calculates `total_amount` as:

```python
total_amount = quantity * unit_price
```

### 3. Validate

The validation functions check:

- duplicate customer, product, and order IDs;
- missing required fields;
- invalid quantities;
- zero or negative prices;
- invalid order dates;
- customer IDs that do not exist;
- product IDs that do not exist;
- unsupported payment statuses;
- unsupported order statuses.

Each rejected record receives an `error_reason` column explaining why it failed validation.

### 4. Save rejected records

Rejected records are saved separately for inspection:

```text
data/errors/customer_errors.csv
data/errors/product_errors.csv
data/errors/order_errors.csv
```

The pipeline does not silently delete invalid records.

### 5. Load valid records

Validated customers, products, and orders are loaded into PostgreSQL tables using SQLAlchemy.

## Database schema

The database contains three related tables:

- `customers`
- `products`
- `orders`

The schema uses:

- primary keys to identify records uniquely;
- foreign keys to connect orders to customers and products;
- `NOT NULL` constraints for required fields;
- `CHECK` constraints to prevent zero or negative quantities and prices.

### Schema SQL

```sql
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    payment_status VARCHAR(30) NOT NULL,
    order_status VARCHAR(30) NOT NULL,

    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    CONSTRAINT fk_order_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);
```

## SQL reports

The project includes reports for revenue, completed orders, products, customers, and unused products.

### Total revenue from completed paid orders

```sql
SELECT
    SUM(total_amount) AS total_revenue
FROM orders
WHERE payment_status = 'paid'
  AND order_status = 'completed';
```

### Top three completed paid orders by value

```sql
SELECT
    *
FROM orders
WHERE payment_status = 'paid'
  AND order_status = 'completed'
ORDER BY total_amount DESC
LIMIT 3;
```

### Revenue by product

```sql
SELECT
    o.product_id,
    p.product_name,
    SUM(o.total_amount) AS total_revenue
FROM orders AS o
INNER JOIN products AS p
    ON o.product_id = p.product_id
WHERE o.payment_status = 'paid'
  AND o.order_status = 'completed'
GROUP BY
    o.product_id,
    p.product_name
ORDER BY total_revenue DESC;
```

### Number of completed paid orders

```sql
SELECT
    COUNT(*) AS order_count
FROM orders
WHERE payment_status = 'paid'
  AND order_status = 'completed';
```

### Customers with no completed paid order

```sql
SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    c.city
FROM customers AS c
LEFT JOIN orders AS o
    ON c.customer_id = o.customer_id
   AND o.payment_status = 'paid'
   AND o.order_status = 'completed'
WHERE o.order_id IS NULL;
```

### Products that have never appeared in a completed paid order

```sql
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.unit_price
FROM products AS p
LEFT JOIN orders AS o
    ON p.product_id = o.product_id
   AND o.payment_status = 'paid'
   AND o.order_status = 'completed'
WHERE o.order_id IS NULL;
```

## Important database note about `total_amount`

The reports use `total_amount`, but the `orders` table definition above does not create that column. Choose one of these approaches before running the reports.

### Option 1: Add a generated column

```sql
ALTER TABLE orders
ADD COLUMN total_amount NUMERIC(14, 2)
GENERATED ALWAYS AS (quantity * unit_price) STORED;
```

### Option 2: Calculate it in each query

```sql
SELECT
    SUM(quantity * unit_price) AS total_revenue
FROM orders
WHERE payment_status = 'paid'
  AND order_status = 'completed';
```

The generated-column approach keeps `total_amount` available for all reports while ensuring that it is calculated from `quantity` and `unit_price`.

## Testing with pytest

Tests are stored in:

```text
tests/test_pipeline.py
```

The test suite checks:

- customer text standardisation;
- product duplicate handling;
- order type conversion;
- `total_amount` calculation;
- duplicate customer validation;
- missing customer validation;
- invalid product prices;
- unknown customer IDs;
- unknown product IDs;
- invalid dates and quantities;
- valid orders being retained.

Run the tests with:

```bash
pytest -v
```

The tests focus on cleaning and validation and do not require a PostgreSQL connection.

## Logging

The pipeline logs:

- pipeline start and completion;
- extraction counts;
- cleaning counts;
- valid and rejected record counts;
- database connection attempts;
- database loading failures.

Logs are written to:

```text
pipeline.log
```

## Project structure

```text
ecommerce-orders-pipeline/
│
├── data/
│   ├── raw/
│   │   ├── customers.csv
│   │   ├── products.json
│   │   └── orders.csv
│   └── errors/
│       ├── customer_error.csv
│       ├── product_error.csv
│       └── order_error.csv
│
├── sql/
│   ├── schema.sql
│   └── reports.sql
│
├── tests/
│   └── test_pipeline.py
│
├── pipeline.ipynb
├── pipeline.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation

Clone the repository and enter the project directory:

```bash
git clone <your-github-repository-url>
cd ecommerce-orders-pipeline
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Recommended `requirements.txt`:

```text
pandas
sqlalchemy
psycopg
python-dotenv
pytest
jupyter
pyarrow
```

## Environment variables

Create a `.env` file in the project root:

```env
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce_db
```

Never commit the real `.env` file to GitHub. Add it to `.gitignore` and use `.env.example` as a template.

## Running the pipeline

If you are working in Jupyter, run the notebook cells in order:

```text
pipeline.ipynb
```

To export the notebook to a Python script:

```bash
python -m pip install nbconvert
python -m nbconvert --to script pipeline.ipynb
```

Then run the exported script:

```bash
python pipeline.py
```

The bottom of `pipeline.py` should contain:

```python
if __name__ == "__main__":
    run_pipeline()
```

This prevents the full pipeline from running automatically when pytest imports the functions.

## Configuration and security

Database credentials are loaded from environment variables using `python-dotenv`. Credentials are not hardcoded in the Python code and the database password is not written to the logs.

Example `.gitignore` entries:

```text
.env
.venv/
__pycache__/
*.pyc
pipeline.log
errors/
```

## Future improvements

- Add database transactions around the complete load.
- Use PostgreSQL upserts for safe reruns.
- Add explicit primary-key and foreign-key creation to the loading process.
- Add a data-quality summary report.
- Add GitHub Actions to run pytest automatically.
- Schedule the pipeline to run daily.
- Add a dashboard for revenue and customer reports.
