import os
import sys
import datetime
from internetarchive import upload, get_item

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

        # Define metadata for the upload
        # The filename on IA will be the basename of the local file
        file_name_on_ia = os.path.basename(duckdb_file_path)

        # Add a timestamp to the filename on IA to keep historical versions if desired,
        # or use a fixed name to overwrite. For archival, timestamped is better.
        # Example: psi_results_2023-10-27_15-30-00.duckdb
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_filename = f"{os.path.splitext(file_name_on_ia)[0]}_{timestamp}{os.path.splitext(file_name_on_ia)[1]}"

        print(f"Preparing to upload {duckdb_file_path} as {archive_filename} to item {item_identifier}...")

        # Metadata for the specific file being uploaded
        md = {
            'title': f'PSI Audit Results Database ({timestamp})',
            'description': f'DuckDB database containing PageSpeed Insights audit results, collected on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}.',
            'collection': item.metadata.get('collection', 'opensource_data'), # Or a specific collection if known
            'mediatype': 'data', # Or 'database' if preferred by IA for .duckdb files
            'date': datetime.datetime.now().isoformat()
        }

        # Check if item exists, if not, metadata for item creation might be needed for the first upload.
        # For simplicity, this script assumes the item identifier either exists or will be created
        # by the upload if it's the first file. IA typically creates the item if it doesn't exist.

        upload(
            identifier=item_identifier,
            files={archive_filename: duckdb_file_path},
            metadata=md,
            access_key=ia_access_key,
            secret_key=ia_secret_key,
            verbose=True
        )
        print(f"Successfully uploaded {archive_filename} to Internet Archive item {item_identifier}")

    except Exception as e:
        print(f"An error occurred during Internet Archive upload: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
