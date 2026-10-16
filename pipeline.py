import logging
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.dialects.postgresql import insert
import os
#logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
#extract
def extract_csv(filename):
    data = pd.read_csv(filename)
    logger.info("Customers count: %s", len(data))
    return data
def extract_json(filename):
    data = pd.read_json(filename)
    logger.info("Restaurants count: %s", len(data))
    return data
#Transforming
def clean_customers(df):
    df = df.replace("", pd.NA)
    df["customer_id"] = pd.to_numeric(df["customer_id"],errors="coerce")
    df["customer_name"] = df["customer_name"].str.strip().str.title()
    df["email"] = df["email"].str.strip().str.lower()
    df["city"] = df["city"].str.strip().str.title()
    logger.info("Cleaned customers count: %s", len(df))
    return df
def clean_products(df):
    df = df.replace("", pd.NA)
    df["product_id"] = pd.to_numeric(df["product_id"],errors="coerce")
    df["product_name"] = df["product_name"].str.strip().str.title()
    df["category"] = df["category"].str.strip().str.title()
    df["unit_price"] = pd.to_numeric(df["unit_price"],errors="coerce")
    logger.info("Cleaned products count: %s", len(df))
    return df
def clean_orders(df):
    df = df.replace("", pd.NA)
    df["order_id"] = pd.to_numeric(df["order_id"],errors="coerce")
    df["order_date"] = pd.to_datetime(df["order_date"],errors="coerce",format="mixed")
    df["quantity"] = pd.to_numeric(df["quantity"],errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"],errors="coerce")
    df["payment_status"] = df["payment_status"].str.strip().str.lower()
    df["order_status"] = df["order_status"].str.strip().str.lower()
    df["total_amount"] = df["quantity"] * df["unit_price"]
    logger.info("Cleaned orders count: %s", len(df))
    return df
#Validating customers
def validate_customers(df):
    duplicate_customer = df["customer_id"].duplicated()
    invalid = (
        duplicate_customer
        | df["customer_id"].isna() 
        | df["customer_name"].isna() 
        | df["email"].isna() 
        | df["city"].isna() 
        )
    errors_df = df[invalid].copy()
    def get_error_reason(row):
        reasons = []
        if duplicate_customer.loc[row.name]:
            reasons.append("Duplicate customer ID")
        if pd.isna(row["customer_id"]):
            reasons.append("Missing customer ID")
        if pd.isna(row['customer_name']):
            reasons.append("Missing customer name")
        if pd.isna(row['email']):
            reasons.append("Missing email")
        if pd.isna(row['city']):
            reasons.append("Missing city")
        return ", ".join(reasons)
    errors_df['error_reason'] = errors_df.apply(get_error_reason, axis=1)
    valid_df = df[~invalid].copy()
    logger.info("%s Valid customer rows and %s rejected customer rows", len(valid_df), len(errors_df))
    return errors_df, valid_df
#Validating products
def validate_products(df):
    duplicate_product = df["product_id"].duplicated()
    invalid = (
        duplicate_product
        | df["product_id"].isna() 
        | df["product_name"].isna() 
        | df["category"].isna() 
        | df["unit_price"].isna()
        | (df["unit_price"]<=0)
        )
    errors_df = df[invalid].copy()
    def get_error_reason(row):
        reasons = []
        if duplicate_product.loc[row.name]:
            reasons.append("Duplicate product ID")
        if pd.isna(row["product_id"]):
            reasons.append("Missing product ID")
        if pd.isna(row['product_name']):
            reasons.append("Missing product name")
        if pd.isna(row['category']):
            reasons.append("Missing category")
        if pd.isna(row['unit_price']):
            reasons.append("Missing unit price")
        elif (row['unit_price']<=0):
            reasons.append("Unit price is less than or equal to 0")
        return ", ".join(reasons)
    errors_df["error_reason"] = [
    get_error_reason(row)
    for _, row in errors_df.iterrows()
]
    valid_df = df[~invalid].copy()
    logger.info("%s Valid product rows and %s rejected product rows", len(valid_df), len(errors_df))
    return errors_df, valid_df
#Validating orders
def validate_orders(df, df1, df2):
    duplicate_order = df["order_id"].duplicated()
    invalid = (
        duplicate_order
        | ~df["customer_id"].isin(df1["customer_id"]) 
        | ~df["product_id"].isin(df2["product_id"]) 
        |df["customer_id"].isna() 
        | df["product_id"].isna() 
        | df["quantity"].isna() 
        | (df["quantity"]<=0) 
        | df["unit_price"].isna() 
        | (df["unit_price"]<=0) 
        | df["order_date"].isna()
        | ~df["payment_status"].isin(["paid", "pending", "refunded"])
        | ~df["order_status"].isin(["completed", "processing", "cancelled"]) 
        )
    errors_df = df[invalid].copy()
    def get_error_reason(row):
        reasons = []
        if duplicate_order.loc[row.name]:
            reasons.append("Duplicate order ID")
        if pd.isna(row['customer_id']):
            reasons.append("Missing customer ID")
        elif row["customer_id"] not in df1["customer_id"].values:
            reasons.append("Customer ID does not exist")
        if pd.isna(row['product_id']):
            reasons.append("Missing product ID")
        elif row["product_id"] not in df2["product_id"].values:
            reasons.append("Product ID does not exist")
        if pd.isna(row['quantity']):
            reasons.append("Missing quantity")
        elif (row['quantity']<=0):
            reasons.append("Quantity less than or equal to 0")
        if pd.isna(row['unit_price']):
            reasons.append("Missing unit price")
        elif (row['unit_price']<=0):
            reasons.append("Unit_price less than 0")
        if pd.isna(row['order_date']):
            reasons.append("Missing order date")
        if pd.isna(row["payment_status"]):
            reasons.append("Missing payment status")
        elif row["payment_status"] not in ["paid", "pending", "refunded"]:
            reasons.append("Invalid payment status")
        if pd.isna(row["order_status"]):
            reasons.append("Missing order status")
        elif row["order_status"] not in ["completed","processing","cancelled"]:
            reasons.append("Invalid order status")

        return ", ".join(reasons)
    errors_df["error_reason"] = [get_error_reason(row) for _, row in errors_df.iterrows()]
    valid_df = df[~invalid].copy()
    logger.info("%s Valid order rows and %s rejected order rows", len(valid_df), len(errors_df))
    return errors_df, valid_df

#save errors
def save_errors(errors, filename):
    os.makedirs('errors', exist_ok=True)
    output_path = os.path.join("/Users/Marydoris/Cleotha/E-commerce Orders ETL Pipeline/errors", filename)
    errors.to_csv(output_path, index=False)
    logger.info("Saved %s errors to errors/%s", len(errors), output_path)

#Load

def load_to_postgres(df, df1, df2):
    load_dotenv(override=True)
    try:
        logger.info("Connecting to PostgreSQL")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME")
        db_port = os.getenv("DB_PORT", "5432")

        logger.debug("USER: %s", db_user)
        logger.debug("HOST: %s", db_host)
        logger.debug("DATABASE: %s", db_name)

        engine = create_engine(
            f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        df.to_sql("customers", engine, if_exists="replace", index=False)
        df1.to_sql("products", engine, if_exists="replace", index=False)
        df2.to_sql("orders", engine, if_exists="replace", index=False)
        logger.info("Loaded %s customers into PostgreSQL.", len(df))
        logger.info("Loaded %s products into PostgreSQL.", len(df1))
        logger.info("Loaded %s orders into PostgreSQL.", len(df2))
    except Exception:
        logger.exception("Failed to connect to PostgreSQL.")
        raise
#Run pipeline
def run_pipeline():
    logger.info("=" * 40)
    logger.info("Pipeline started")
    
    raw_customers = extract_csv("customers.csv")
    raw_products = extract_json("products.json")
    raw_orders = extract_csv("orders.csv")
    cleaned_customer = clean_customers(raw_customers)
    cleaned_product = clean_products(raw_products)
    cleaned_order = clean_orders(raw_orders)
    customer_error, valid_customer = validate_customers(cleaned_customer)
    product_error, valid_product = validate_products(cleaned_product)
    order_error, valid_order = validate_orders(cleaned_order, valid_customer, valid_product)
    save_errors(customer_error, "customer_error.csv")
    save_errors(product_error, "product_error.csv")
    save_errors(order_error, "order_error.csv")
    load_to_postgres(valid_customer, valid_product, valid_order)
    
    logger.info("Pipeline completed successfully")
    logger.info("=" * 40)

if __name__ == '__main__':
    run_pipeline()
    