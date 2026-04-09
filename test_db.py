import subprocess
from io import StringIO
import pandas as pd

CONTAINER_NAME = "postgres-m3-int"
DB_NAME = "amman_market"
DB_USER = "postgres"


def read_table(table_name: str) -> pd.DataFrame:
    """Read a table from PostgreSQL inside the Docker container."""
    query = f"COPY (SELECT * FROM {table_name}) TO STDOUT WITH CSV HEADER"

    cmd = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-c",
        query,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to read table '{table_name}'.\n{result.stderr}"
        )

    return pd.read_csv(StringIO(result.stdout))


def main():
    # Load tables
    customers = read_table("customers")
    products = read_table("products")
    orders = read_table("orders")
    order_items = read_table("order_items")

    # Basic table shapes
    print("=== Table Shapes ===")
    print("customers:", customers.shape)
    print("products:", products.shape)
    print("orders:", orders.shape)
    print("order_items:", order_items.shape)

    # Order status distribution
    print("\n=== Order Status Distribution ===")
    print(orders["status"].value_counts())

    # Suspicious quantities
    print("\n=== Suspicious Quantities (>100) ===")
    print(order_items[order_items["quantity"] > 100].shape)

    # Missing / city distribution
    print("\n=== City Distribution (including missing values) ===")
    print(customers["city"].value_counts(dropna=False))

    # Category distribution
    print("\n=== Product Category Distribution ===")
    print(products["category"].value_counts())

    # Optional: preview a few rows
    print("\n=== Sample Customers ===")
    print(customers.head())

    print("\n=== Sample Orders ===")
    print(orders.head())

    print("\n=== Sample Order Items ===")
    print(order_items.head())

    print("\n=== Sample Products ===")
    print(products.head())


if __name__ == "__main__":
    main()