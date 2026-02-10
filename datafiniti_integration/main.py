#!/usr/bin/env python3
"""CLI entry point for the Datafiniti -> OpenAI feed converter."""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any, Dict, List, Optional

if __package__ is None:
    import pathlib
    import sys as _sys

    _sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datafiniti_integration.datafiniti_to_openai_feed import (
    DATAFINITI_FETCH_FORMAT,
    DEFAULT_POLL_SECONDS,
    LOG_FORMAT,
    convert_record_to_feed,
    datafiniti_search,
    load_env_file,
    smartersorting_enrich,
    write_feed,
)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command‑line arguments for the script."""
    parser = argparse.ArgumentParser(description="Retrieve Datafiniti products, optionally enrich, and output a ChatGPT feed.")
    parser.add_argument("--env", default=".env", help="Path to a .env file containing API keys (default: .env).")
    parser.add_argument("--query", required=True, help="Datafiniti query string. See Datafiniti docs for syntax.")
    parser.add_argument("--num-records", type=int, default=10, help="Maximum number of records to fetch (default: 10). For bulk download specify larger value and add --download.")
    parser.add_argument("--view", default=None, help="Optional Datafiniti view (e.g. product_flat_prices).")
    parser.add_argument("--download", action="store_true", help="Initiate a bulk download instead of a preview search.")
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=DEFAULT_POLL_SECONDS,
        help="Maximum time to wait for bulk downloads in seconds (default: 600).",
    )
    parser.add_argument("--enrich", action="store_true", help="Enable SmarterSorting enrichment (requires SMARTERSORTING_API_KEY in .env).")
    parser.add_argument("--seller-name", default=None, help="Optional seller or retailer name to include in the feed.")
    parser.add_argument("--output-file", required=True, help="Path to write the output feed (JSONL or CSV). Use .gz extension to enable compression.")
    parser.add_argument("--format", default="jsonl", choices=["jsonl", "csv"], help="Output feed format (jsonl or csv). Default: jsonl.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    # Load API keys from .env if provided.
    load_env_file(args.env)
    datafiniti_api_key = os.environ.get("DATAFINITI_API_KEY")
    if not datafiniti_api_key:
        logging.error("Missing DATAFINITI_API_KEY. Set it in your .env file or environment.")
        raise RuntimeError("Missing DATAFINITI_API_KEY. Set it in your .env file or environment.")
    smartersorting_api_key = os.environ.get("SMARTERSORTING_API_KEY")
    if args.enrich and not smartersorting_api_key:
        logging.warning(
            "SMARTERSORTING_API_KEY not found. Enrichment will be skipped even though --enrich was set."
        )

    # Determine compression from filename.
    compress = args.output_file.endswith(".gz")

    # Fetch products from Datafiniti.
    logging.info("Querying Datafiniti for '%s' ...", args.query)
    records, download_id = datafiniti_search(
        api_key=datafiniti_api_key,
        query=args.query,
        num_records=args.num_records,
        view=args.view,
        download=args.download,
        fmt=DATAFINITI_FETCH_FORMAT,
        poll_seconds=args.poll_seconds,
    )
    logging.info("Retrieved %d record(s) from Datafiniti.", len(records))
    if args.download and download_id:
        logging.info("Download job ID: %s", download_id)

    # Prepare feed records.
    feed_records: List[Dict[str, Any]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        enrich_payload: Optional[Dict[str, Any]] = None
        if args.enrich:
            upc = rec.get("upc") or (rec.get("gtins") or [None])[0]
            if upc and smartersorting_api_key:
                try:
                    enrich_payload = smartersorting_enrich(
                        api_key=smartersorting_api_key,
                        upc=str(upc),
                        product_name=rec.get("name"),
                        user_id=args.seller_name,
                    )
                except Exception as exc:
                    logging.warning("Enrichment failed for UPC %s: %s", upc, exc)
            elif upc and not smartersorting_api_key:
                logging.debug("Skipping enrichment for UPC %s because SMARTERSORTING_API_KEY is missing.", upc)
        feed_record = convert_record_to_feed(rec, enrich=enrich_payload, seller_name=args.seller_name)
        feed_records.append(feed_record)

    # Write feed to disk.
    logging.info("Writing feed to %s ...", args.output_file)
    write_feed(feed_records, args.output_file, compress=compress, fmt=args.format)
    logging.info("Done.")


if __name__ == "__main__":
    main()
