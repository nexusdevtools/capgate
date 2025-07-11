# capgate/brain/trainer.py

import json
import os
import csv
from typing import List, Optional
from base.logger import logger


def jsonl_to_csv(jsonl_path: str, csv_path: Optional[str] = None, fields: Optional[List[str]] = None):
    """
    Convert a JSONL event log into a flat CSV file.
    Useful for quick ML training or data visualization.
    """
    if not os.path.exists(jsonl_path):
        logger.error(f"❌ File not found: {jsonl_path}")
        return

    csv_path = csv_path or jsonl_path.replace(".jsonl", ".csv")

    try:
        with open(jsonl_path, "r") as jsonl_file:
            lines = [json.loads(line) for line in jsonl_file if line.strip()]

        if not lines:
            logger.warning("⚠️ No data found in JSONL file.")
            return

        if not fields:
            # Flattened top-level structure for ML use
            fields = ["timestamp", "type", "id"] + list(lines[0].get("data", {}).keys())

        with open(csv_path, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fields)
            writer.writeheader()

            for entry in lines:
                row = {
                    "timestamp": entry.get("timestamp"),
                    "type": entry.get("type"),
                    "id": entry.get("id")
                }
                row.update(entry.get("data", {}))
                writer.writerow(row)

        logger.info(f"📊 Converted {len(lines)} entries to CSV: {csv_path}")

    except Exception as e:
        logger.error(f"❌ Failed to convert JSONL to CSV: {e}")


if __name__ == "__main__":
    path = "/home/nexus/capgate/data/brain_feed/event_log_*.jsonl"  # Change to your file
    jsonl_to_csv(jsonl_path=path)
    # Example usage
    # jsonl_to_csv("path/to/your/event_log.jsonl", "output.csv
    # fields=["timestamp", "type", "id", "data_field1", "data_field2"])
    # This will convert the JSONL file to a CSV file with the specified fields.
    # If fields are not specified, it will use all available fields in the first entry.
    # If the JSONL file is empty, it will log a warning and exit gracefully.
    # If the JSONL file does not exist, it will log an error and exit gracefully.
    # The output CSV file will be created in the same directory as the JSONL file,
    # with the same name but with a .csv extension.
    # If the JSONL file is malformed, it will log an error and exit gracefully.
    # If the CSV file already exists, it will be overwritten.
    # If the CSV file cannot be created, it will log an error and exit gracefully.
    