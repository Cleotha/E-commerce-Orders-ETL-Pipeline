# E-commerce Orders ETL Pipeline

A Python-based ETL pipeline that extracts e-commerce data from CSV and JSON files, cleans and validates the data, identifies invalid records, and loads valid records into PostgreSQL for business analysis.

The project demonstrates core data engineering concepts, including data ingestion, transformation, data quality validation, error handling, relational database design, automated testing, and analytical SQL.

## Project Overview

E-commerce businesses generate data about customers, products, and orders. Before this data can support reliable business decisions, it must be cleaned, validated, and stored in a structured database.

This project automates that process by building an ETL pipeline that transforms raw customer, product, and order data into structured, analysis-ready tables in PostgreSQL.

## Tech Stack

- **Python** — ETL orchestration and data processing
- **Pandas** — Data cleaning, transformation, and validation
- **PostgreSQL** — Relational database storage
- **SQLAlchemy** — Database connectivity and data loading
- **pytest** — Automated unit testing
- **Python Logging** — Pipeline execution and error monitoring
- **python-dotenv** — Environment variable management
- **Git and GitHub** — Version control and project management

## Architecture

```text
          Raw Data Sources
                 |
        +--------+--------+
        |        |        |
   customers   products  orders
      .csv      .json     .csv
        |        |        |
        +--------+--------+
                 |
             Extraction
                 |
          Data Cleaning
                 |
          Data Validation
                 |
          +------+------+
          |             |
      Valid Data    Rejected Data
          |             |
          |        Error Reason
          |             |
          |       CSV Error Files
          |
     PostgreSQL
          |
   SQL Business Analysis
```

## Project Structure

```text
E-commerce-Orders-ETL-Pipeline/
│
├── customers.csv
├── products.json
├── orders.csv
├── pipeline.py
├── test_pipeline.py
├── requirements.txt
├── .env.example
├── .gitignore
├── pipeline.log
├── errors/
│   ├── customer_error.csv
│   ├── product_error.csv
│   └── order_error.csv
└── README.md
```

*Note: The `errors/` directory and `pipeline.log` are generated or updated when the pipeline runs. Their presence depends on execution and repository configuration.*

## ETL Workflow

### 1. Extract

The pipeline reads data from three source files:

- `customers.csv` — customer information
- `products.json` — product details
- `orders.csv` — customer purchase records

Pandas is used to load the source files into DataFrames.

### 2. Transform

The pipeline prepares the data for validation and loading by:

- Converting identifier and numeric columns to numeric types
- Parsing order dates
- Removing leading and trailing whitespace
- Standardizing customer names, cities, and product names
- Converting email addresses to lowercase
- Normalizing payment and order statuses
- Converting empty strings to missing values

### 3. Validate

The pipeline checks records for data quality issues.

**Customer validation**
- Missing customer IDs
- Duplicate customer IDs
- Missing customer names, emails, or cities

**Product validation**
- Missing product IDs or required fields
- Duplicate product IDs
- Missing, zero, or negative product prices

**Order validation**
- Duplicate order IDs
- Missing or invalid order dates
- Missing or unknown customer and product IDs
- Missing, zero, or negative quantities
- Missing, zero, or negative unit prices
- Invalid payment statuses
- Invalid order statuses

Rejected records receive an `error_reason` field explaining the validation issue. Valid records continue to the loading stage.

### 4. Load

Valid customer, product, and order records are loaded into PostgreSQL using Pandas and SQLAlchemy.

The database schema uses:

- Primary keys to identify records
- Foreign keys to maintain relationships between orders, customers, and products
- `NOT NULL` constraints for required fields
- `CHECK` constraints for positive prices and quantities
- A generated `total_amount` column for order value calculation

The current loading strategy uses append mode. Re-running the pipeline with existing primary keys may cause conflicts; safe, repeatable loading is a planned improvement.

### 5. Error Handling and Logging

The pipeline records execution messages using Python's `logging` module.

Logs are written to:
- The terminal
- `pipeline.log`

Rejected customer, product, and order records are exported to CSV files for inspection and correction.

## Database Schema

The pipeline uses three related PostgreSQL tables.

| Table | Purpose |
|---|---|
| `customers` | Stores customer details |
| `products` | Stores product information and unit prices |
| `orders` | Stores order details and references customers and products |

The `orders` table includes a generated `total_amount` column calculated as:

```sql
quantity * unit_price
```

This supports revenue and customer spending analysis.

## Business Analysis

The project includes SQL queries designed to answer practical business questions:

1. **Total revenue:** What is the revenue from paid, completed orders?
2. **Top customers:** Which three customers have spent the most on paid, completed orders?
3. **Revenue by category:** Which product categories generate the most revenue?
4. **Completed order count:** How many orders are both paid and completed?
5. **Customers without orders:** Which customers have never placed an order?
6. **Products without orders:** Which products have never been ordered?

These queries demonstrate the use of joins, aggregation, filtering, grouping, sorting, and subpopulation analysis.

## Getting Started

### Prerequisites

Install the following before running the project:

- Python 3.10 or later
- PostgreSQL
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Cleotha/E-commerce-Orders-ETL-Pipeline.git
cd E-commerce-Orders-ETL-Pipeline
```

### 2. Create a Virtual Environment

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Ensure `requirements.txt` includes the libraries used by the project, including Pandas, SQLAlchemy, the PostgreSQL driver, and python-dotenv. Include pytest if you want to run the tests.

### 4. Configure Environment Variables

Create a `.env` file in the project root based on `.env.example`.

Example:

```dotenv
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce_db
```

Replace the example values with your PostgreSQL credentials. Do not commit your real `.env` file or database passwords to GitHub.

### 5. Create the Database and Tables

Create the database in PostgreSQL, then execute your SQL schema script to create the `customers`, `products`, and `orders` tables before running the pipeline.

Make sure the tables and their constraints match the column names and data types in the source data.

### 6. Run the Pipeline

```bash
python pipeline.py
```

The pipeline will extract the source data, clean and validate records, save rejected records, and load valid records into PostgreSQL.

Check the terminal output and `pipeline.log` for execution details.

### 7. Run the Tests

```bash
pytest -v
```

The test suite covers data cleaning, data type conversions, validation rules, foreign-key checks, duplicate identifiers, invalid statuses, and rejected-record reasons.

Run the tests locally to confirm the current code passes before reporting test results.

## Data Quality and Testing

Data quality is a key component of this project. The pipeline separates invalid records from valid records rather than allowing all raw data to flow directly into the database.

The pytest suite uses sample DataFrames to test individual cleaning and validation functions. This helps detect regressions when pipeline logic changes.

Future testing improvements include integration tests for PostgreSQL loading, error-file generation, and repeated pipeline execution.

## Current Limitations

- Loading existing IDs again can trigger primary-key conflicts.
- Database table creation is handled separately from the ETL script.
- Error-file output paths should remain portable across operating systems.
- The project currently uses local files as source data.
- Automated continuous integration has not yet been configured.

## Future Improvements

- Implement idempotent database loading using PostgreSQL upserts.
- Add transactional loading and stronger database failure recovery.
- Add automated tests for database integration and repeat runs.
- Configure GitHub Actions to run tests on every push and pull request.
- Introduce Apache Airflow for workflow orchestration.
- Containerize the application and database with Docker Compose.
- Explore AWS services for cloud-based storage, processing, and deployment.
- Add data quality metrics and pipeline monitoring.

## Key Learning Outcomes

Through this project, I practised:

- Building an end-to-end ETL workflow with Python
- Processing CSV and JSON datasets with Pandas
- Cleaning and validating messy data
- Tracking rejected records with explicit error reasons
- Designing relational schemas and database constraints
- Loading data into PostgreSQL using SQLAlchemy
- Writing SQL queries for business reporting
- Writing unit tests with pytest
- Using logging to monitor pipeline execution
- Managing configuration through environment variables

## Author

**Data Engineering Learner**

GitHub: [Cleotha](https://github.com/Cleotha)

This project is part of my practical journey toward building reliable, testable, and production-minded data pipelines.
