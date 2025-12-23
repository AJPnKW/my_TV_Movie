import json
from pathlib import Path
from genson import SchemaBuilder
import logging
import sys
from datetime import datetime

# Setup logging immediately
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "generate_schema.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.debug("=== Script started ===")
logging.debug(f"Log file: {LOG_FILE}")
logging.debug(f"Current directory: {Path.cwd()}")

try:
    DATA_DIR = Path(__file__).parent.parent / "data"
    OUTPUT_FILE = Path(__file__).parent.parent / "schema.json"
    input_file = DATA_DIR / "data.json"

    logging.debug(f"Data directory: {DATA_DIR}")
    logging.debug(f"Input file: {input_file}")
    logging.debug(f"Output file: {OUTPUT_FILE}")

    if not input_file.exists():
        raise FileNotFoundError(f"data.json not found at {input_file}")

    logging.info("Loading data.json...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logging.info(f"Data loaded. Type: {type(data)}")

    builder = SchemaBuilder()
    builder.add_object(data)
    schema = builder.to_schema()

    logging.info("Writing schema.json...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2)

    logging.info(f"Schema saved to: {OUTPUT_FILE}")

except Exception as e:
    logging.exception(f"Script crashed: {e}")

finally:
    logging.debug("=== Script ended ===")
    print("\nScript finished. Check logs/generate_schema.log for details.")
    input("\nPress Enter to exit...")
