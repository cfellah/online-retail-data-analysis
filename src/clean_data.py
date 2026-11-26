
import pandas as pd
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "online_retail_cleaned.csv"


def impute_zero_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute zero unit prices using historical prices for each product.

    Rules:
    - If previous and next positive prices exist: use their average.
    - If only one reference price exists: use that price.
    - If no positive reference price exists: keep zero.

    Adds a boolean column 'PriceEstimated' to track imputed prices.
    """

    df = df.copy()

    # Sort transactions chronologically by product
    df = df.sort_values(
        ["StockCode", "InvoiceDate"]
    ).copy()

    # Identify positive reference prices
    known_prices = df["UnitPrice"].where(
        df["UnitPrice"] > 0
    )

    # Find previous and next positive prices per product
    previous_price = (
        known_prices.groupby(df["StockCode"]).ffill()
    )

    next_price = (
        known_prices.groupby(df["StockCode"]).bfill()
    )

    # Estimate prices
    estimated_price = (previous_price + next_price) / 2

    # Use the available reference when only one exists
    estimated_price = estimated_price.fillna(next_price)
    estimated_price = estimated_price.fillna(previous_price)

    # Identify zero prices that can be estimated
    zero_mask = df["UnitPrice"] == 0
    estimated_mask = zero_mask & estimated_price.notna()

    # Track estimated prices
    df["PriceEstimated"] = estimated_mask

    # Replace estimable zero prices
    df.loc[estimated_mask, "UnitPrice"] = (
        estimated_price[estimated_mask]
    )

    # Restore original row order
    df = df.sort_index()

    return df



def extract_data(file_path: Path) -> pd.DataFrame:
    """
    Extract data from the original Excel file.
    """
    print("Extracting data...")

    df = pd.read_excel(file_path)

    print(f"Extraction completed: {df.shape[0]} rows, {df.shape[1]} columns.")

    return df




def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and transform the extracted dataset.
    """
    print("Transforming data...")

    # Work on a copy to preserve the original dataset
    df = df.copy()

    # Remove exact duplicate rows
    df = df.drop_duplicates().copy()

    # Standardize CustomerID to string
    df["CustomerID"] = df["CustomerID"].astype("string")

    # Identify invoices with at least one known CustomerID
    invoice_customer_mapping = (
        df.groupby("InvoiceNo")["CustomerID"]
        .first()
    )

    # Fill missing CustomerIDs when an invoice has a known customer
    df["CustomerID"] = df["CustomerID"].fillna(
        df["InvoiceNo"].map(invoice_customer_mapping)
    )

    # Assign a unique synthetic CustomerID to invoices
    # with no known customer
    missing_customer_mask = df["CustomerID"].isna()

    df.loc[missing_customer_mask, "CustomerID"] = (
        "UNKNOWN_" +
        df.loc[missing_customer_mask, "InvoiceNo"].astype(str)
    )

    # Impute zero unit prices
    df = impute_zero_prices(df)

    # Display price imputation results
    print(
        f"Zero prices estimated: {df['PriceEstimated'].sum()}"
    )
    print(
        f"Zero prices remaining: {(df['UnitPrice'] == 0).sum()}"
    )

    # Create business indicators
    df["IsCancellation"] = (
        df["InvoiceNo"].astype(str).str.startswith("C")
    )

    df["IsNegativeTransaction"] = (
        df["Quantity"] < 0
    )

    print(
        f"Transformation completed: "
        f"{df.shape[0]} rows, {df.shape[1]} columns."
    )

    return df




def load_data(df: pd.DataFrame, output_path: Path) -> None:
    """
    Load the transformed dataset into a CSV file.
    """
    print("Loading data...")

    # Create the output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export the transformed dataset
    df.to_csv(output_path, index=False)

    print(f"Data successfully saved to: {output_path}")




if __name__ == "__main__":

    # 1. Extract
    df = extract_data(RAW_FILE)

    # 2. Transform
    df_transformed = transform_data(df)

    # 3. Load
    load_data(df_transformed, OUTPUT_FILE)

    print("\nETL process completed successfully!")

    df_test = pd.read_csv(OUTPUT_FILE, dtype={"CustomerID": "string"})

    print("Valeurs manquantes :", df_test["CustomerID"].isna().sum())

    print(
        "Identifiants fictifs :",
        df_test["CustomerID"].str.startswith("UNKNOWN_").sum()
    )

