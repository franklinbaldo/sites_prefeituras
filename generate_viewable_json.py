import duckdb
import json
import sys
import os

def generate_json_from_duckdb(db_file_path, output_json_path):
    """
    Connects to a DuckDB database, queries for the latest PSI metrics per URL,
    and saves the result as a JSON file.
    """
    if not os.path.exists(db_file_path):
        print(f"Error: Database file not found at {db_file_path}")
        sys.exit(1)

    try:
        con = duckdb.connect(database=db_file_path, read_only=True)
        print(f"Successfully connected to {db_file_path}")

        # Query to get the latest record for each URL
        # Assumes 'psi_metrics' table and 'timestamp', 'url' columns exist.
        query = """
        SELECT *
        FROM psi_metrics
        QUALIFY ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC) = 1;
        """

        results = con.execute(query).fetchall()
        column_names = [desc[0] for desc in con.description]

        # Convert list of tuples to list of dictionaries
        data_for_json = []
        for row in results:
            data_for_json.append(dict(zip(column_names, row)))

        con.close()

        # Ensure the output directory exists
        output_dir = os.path.dirname(output_json_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory {output_dir}")

        with open(output_json_path, 'w') as f:
            json.dump(data_for_json, f, indent=2)

        print(f"Successfully generated JSON ({len(data_for_json)} records) at {output_json_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
        if 'con' in locals() and con:
            con.close()
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python generate_viewable_json.py <path_to_duckdb_file> <output_json_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    json_path = sys.argv[2]
    generate_json_from_duckdb(db_path, json_path)
