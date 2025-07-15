import os
import sys
import datetime
import tempfile
import duckdb
from pathlib import Path
from internetarchive import upload, get_item

def export_duckdb_to_parquet(duckdb_path: str, output_path: str) -> None:
    """
    Export DuckDB data to Parquet format.

    Args:
        duckdb_path: Path to the DuckDB file
        output_path: Path where the Parquet file will be saved
    """
    conn = duckdb.connect(duckdb_path)

    # Get table names from the database
    tables = conn.execute("SHOW TABLES").fetchall()

    if not tables:
        print("Warning: No tables found in the database")
        return

    # For simplicity, export all tables to a single parquet file
    # If there are multiple tables, you might want to union them or handle differently
    table_name = tables[0][0]

    # Use DuckDB's native COPY command to export to Parquet
    conn.execute(f"""
    COPY (SELECT * FROM {table_name})
    TO '{output_path}' (FORMAT PARQUET, PARTITION_BY (date(timestamp), strategy), OVERWRITE_OR_IGNORE)
    """)

    conn.close()
    print(f"Successfully exported DuckDB data to Parquet: {output_path}")

def main():
    item_identifier = os.getenv('IA_ITEM_IDENTIFIER')
    ia_access_key = os.getenv('IA_ACCESS_KEY')
    ia_secret_key = os.getenv('IA_SECRET_KEY')
    duckdb_file_path = os.getenv('DUCKDB_FILE_PATH')

    if not all([item_identifier, ia_access_key, ia_secret_key, duckdb_file_path]):
        print("Error: Missing one or more required environment variables:")
        print("IA_ITEM_IDENTIFIER, IA_ACCESS_KEY, IA_SECRET_KEY, DUCKDB_FILE_PATH")
        sys.exit(1)

    if not os.path.exists(duckdb_file_path):
        print(f"Error: DuckDB file not found at {duckdb_file_path}")
        sys.exit(1)

    try:
        print(f"Fetching item '{item_identifier}' from Internet Archive...")
        item = get_item(item_identifier)

        # Create a temporary directory to store the partitioned parquet files
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Exporting DuckDB data to Parquet format in {temp_dir}...")
            export_duckdb_to_parquet(duckdb_file_path, temp_dir)

            # Create a tarball of the partitioned data
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            archive_filename_base = f"psi_results_{timestamp}"
            archive_path = f"/tmp/{archive_filename_base}.tar.gz"

            import tarfile
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(temp_dir, arcname=archive_filename_base)

            print(f"Preparing to upload {archive_path} to item {item_identifier}...")

            # Metadata for the specific file being uploaded
            md = {
                'title': f'PSI Audit Results Dataset ({timestamp})',
                'description': f'Parquet dataset containing PageSpeed Insights audit results, collected on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}. Exported from DuckDB database.',
                'collection': item.metadata.get('collection', 'opensource_data'), # Or a specific collection if known
                'mediatype': 'data', # Data format for parquet files
                'date': datetime.datetime.now().isoformat()
            }

            # Check if item exists, if not, metadata for item creation might be needed for the first upload.
            # For simplicity, this script assumes the item identifier either exists or will be created
            # by the upload if it's the first file. IA typically creates the item if it doesn't exist.

            upload(
                identifier=item_identifier,
                files={f"{archive_filename_base}.tar.gz": archive_path},
                metadata=md,
                access_key=ia_access_key,
                secret_key=ia_secret_key,
                verbose=True
            )
            print(f"Successfully uploaded {archive_filename_base}.tar.gz to Internet Archive item {item_identifier}")

            # Clean up temporary file
            os.unlink(archive_path)

    except Exception as e:
        print(f"An error occurred during Internet Archive upload: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
