#!/usr/bin/env python3
"""Utilities for retrieving product data from Datafiniti, optionally enriching it
via SmarterSorting and converting the result into the official ChatGPT
product feed format.

This module provides library functions and helpers for working with Datafiniti
and SmarterSorting. A standalone command‑line wrapper is provided in
datafiniti_integration/main.py (run via `python -m datafiniti_integration.main`)
for users who prefer a CLI experience.

High‑level workflow (library usage):

1. Perform a search against the Datafiniti product API using your API key from
   a .env file and boolean query parameters.  You can specify the number of
   records to
   retrieve (`--num-records`) and optionally request a bulk download.
2. (Optional) For each product returned, call the SmarterSorting public
   enrichment API to normalize and augment the record.  Enrichment is keyed
   off of UPC/GTIN codes.  This step is enabled via `--enrich`.
3. Convert each product record into the ChatGPT Commerce feed schema.  Many
   fields are mapped directly from Datafiniti (e.g. `name` → `title`,
   `brand` → `brand`).  If enrichment is enabled, enriched fields take
   precedence for missing or empty values.
4. Write the feed as a newline‑delimited JSON file (`.jsonl`) or as a CSV
   depending on your preference.  The output can optionally be gzip‑compressed.

CLI usage:

The CLI examples previously shown in this module are available via the
project's CLI entrypoint. Example invocations:

     python -m datafiniti_integration.main \
        --query "categories:shoes AND categories:women" \
        --num-records 50 \
        --output-file my_feed.jsonl

     # With enrichment enabled:
     python -m datafiniti_integration.main \
        --enrich \
        --query "gtins:*" \
        --num-records 10 \
        --output-file feed_with_enrichment.jsonl.gz

See datafiniti_integration/main.py and README.md for detailed instructions.
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple

from datafiniti_integration.env_utils import load_env_file
from datafiniti_integration.http_utils import http_get_json, http_post_json

# Base URLs for Datafiniti and SmarterSorting.
DATAFINITI_SEARCH_URL = "https://api.datafiniti.co/v4/products/search"
DATAFINITI_DOWNLOAD_URL = "https://api.datafiniti.co/v4/downloads/{id}"
SMARTERSORTING_URL = "https://ui-enrichment-service-api-production-905356271911.us-central1.run.app/api/enrich_public"
DATAFINITI_FETCH_FORMAT = "JSON"
LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_POLL_SECONDS = 600
POLL_INTERVAL_SECONDS = 2


def datafiniti_search(
    api_key: str,
    query: str,
    num_records: Optional[int] = None,
    view: Optional[str] = None,
    download: bool = False,
    fmt: str = "JSON",
    poll_seconds: int = DEFAULT_POLL_SECONDS,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Search Datafiniti products API and return records.

    If download is False, this function returns the first ``num_records`` records
    directly from the search endpoint (up to 10 records).  If download is True,
    it initiates a bulk download and returns the final list of records once the
    job is complete.  When download is enabled, ``num_records`` controls how
    many records to retrieve from the download; omit to fetch all matching
    results.

    Args:
        api_key: Your Datafiniti API token.
        query: Boolean query string.
        num_records: Maximum number of records to return.
        view: Optional Datafiniti view (e.g. "product_flat_prices").
        download: Whether to issue a bulk download request.
        fmt: Output format ("JSON" or "CSV").

    Returns:
        A tuple of (records, download_id).  ``download_id`` is only present when
        ``download`` is True and may be used for debugging.

    Raises:
        RuntimeError: If the API returns an error or the download cannot be
        retrieved.
    """
    payload: Dict[str, Any] = {"query": query}
    if num_records is not None:
        payload["num_records"] = num_records
    if view:
        payload["view"] = view
    payload["format"] = fmt.upper()
    if download:
        payload["download"] = True

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    resp_json = http_post_json(DATAFINITI_SEARCH_URL, payload, headers)

    # Non‑download search returns data immediately.
    if not download:
        records = resp_json.get("records") or []
        if not isinstance(records, list):
            raise RuntimeError("Unexpected response structure: expected 'records' to be a list.")
        return records, None

    # Download flow: poll until status=completed.
    download_id = str(resp_json.get("id") or resp_json.get("_id") or "")
    if not download_id:
        raise RuntimeError("No download ID returned from Datafiniti.")

    # Poll for completion.
    poll_url = DATAFINITI_DOWNLOAD_URL.format(id=download_id)
    max_attempts = max(1, poll_seconds // POLL_INTERVAL_SECONDS)
    consecutive_errors = 0
    max_consecutive_errors = max(3, max_attempts // 10)
    for attempt in range(max_attempts):
        try:
            body = http_get_json(poll_url, headers, timeout=30)
            consecutive_errors = 0
        except RuntimeError:
            consecutive_errors += 1
            logging.warning(
                "Polling download %s failed (%d/%d consecutive errors). Retrying...",
                download_id,
                consecutive_errors,
                max_consecutive_errors,
            )
            if consecutive_errors >= max_consecutive_errors:
                raise RuntimeError(
                    f"Polling download {download_id} failed after {consecutive_errors} consecutive errors."
                )
            time.sleep(POLL_INTERVAL_SECONDS)
            continue
        status = body.get("status", "").lower()
        if status in {"failed", "error"}:
            raise RuntimeError(f"Download {download_id} failed with status '{status}'.")
        if status == "completed":
            break
        time.sleep(POLL_INTERVAL_SECONDS)
    else:
        raise RuntimeError(
            f"Download {download_id} did not complete in time after {max_attempts * POLL_INTERVAL_SECONDS} seconds."
        )

    result_urls = body.get("results") or []
    records: List[Dict[str, Any]] = []
    for url in result_urls:
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                # Datafiniti returns JSON lines when format=JSON.
                for line in resp.read().decode("utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception as exc:
                        logging.warning("Skipping malformed JSON line from download results: %s", exc)
                        continue
        except Exception as exc:
            raise RuntimeError(f"Failed to download results from {url}: {exc}") from exc
    return records, download_id


def smartersorting_enrich(
    api_key: str,
    upc: str,
    product_name: Optional[str] = None,
    user_id: Optional[str] = None,
    enable_async_enrichment: Optional[bool] = None,
    re_enrich: Optional[bool] = None,
) -> Dict[str, Any]:
    """Call the SmarterSorting enrichment API for a single UPC.

    Args:
        api_key: Your SmarterSorting API token.
        upc: The UPC/GTIN of the product to enrich.
        product_name: Optional product name to assist enrichment.
        user_id: Optional user identifier for caching.
        enable_async_enrichment: Switch to asynchronous enrichment mode when explicitly set.
        re_enrich: Force re‑enrichment even if cached.

    Returns:
        The enriched product JSON.  This may include keys such as
        ``canonicalBrand``, ``canonicalDescription``, or other proprietary
        fields.  The exact schema is defined by SmarterSorting and may vary.

    Raises:
        RuntimeError: If the API call fails.
    """
    payload: Dict[str, Any] = {"upc": upc}
    if product_name:
        payload["product_name"] = product_name
    if user_id:
        payload["user_id"] = user_id
    if enable_async_enrichment is not None:
        payload["enable_async_enrichment"] = enable_async_enrichment
    if re_enrich is not None:
        payload["re_enrich"] = re_enrich

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    return http_post_json(SMARTERSORTING_URL, payload, headers)


def convert_record_to_feed(
    rec: Dict[str, Any],
    enrich: Optional[Dict[str, Any]] = None,
    seller_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a Datafiniti product record (optionally enriched) into feed format.

    The ChatGPT product feed format contains a large number of optional fields.
    This function maps a subset of Datafiniti fields to the feed spec.  If an
    enriched record is provided, its values override missing or empty values
    from the base record.  Unknown keys in the enriched payload are ignored.

    Args:
        rec: The original Datafiniti product record.
        enrich: Optional SmarterSorting enrichment result.
        seller_name: Optional merchant or retailer name to include.

    Returns:
        A dictionary containing feed attributes.
    """
    feed: Dict[str, Any] = {}
    # Required eligibility flags: always searchable; checkout disabled by default.
    feed["is_eligible_search"] = "true"
    feed["is_eligible_checkout"] = "false"

    # Unique item identifier.  Prefer Datafiniti id, fallback to key(s).
    keys_value = rec.get("keys")
    if isinstance(keys_value, list) and keys_value:
        fallback_item_id = keys_value[0]
    elif isinstance(keys_value, str):
        fallback_item_id = keys_value
    else:
        fallback_item_id = ""
    feed["item_id"] = rec.get("id") or fallback_item_id

    # Identifiers: GTIN/UPC/EAN.
    gtins = None
    for field in ("gtins", "upc", "ean", "ean13", "ean8", "upca", "upce"):
        value = rec.get(field)
        if value:
            gtins = value
            break
    if isinstance(gtins, list) and gtins:
        feed["gtin"] = gtins[0]
    elif isinstance(gtins, str):
        feed["gtin"] = gtins

    # Manufacturer part number.
    mpn = rec.get("manufacturerNumber") or rec.get("mpn")
    if mpn:
        feed["mpn"] = mpn

    # SKU: take first SKU entry if nested.
    skus = rec.get("skus") or rec.get("sku")
    if skus:
        if isinstance(skus, list):
            first = skus[0]
            if isinstance(first, dict):
                feed["sku"] = first.get("value") or first.get("sku")
            else:
                feed["sku"] = first
        elif isinstance(skus, dict):
            feed["sku"] = skus.get("value") or skus.get("sku")
        else:
            feed["sku"] = skus

    # Basic attributes.
    feed["title"] = rec.get("name") or rec.get("title") or ""
    # Description: pick the first description value if present.
    description = ""
    desc_list = rec.get("descriptions") or []
    if isinstance(desc_list, list):
        for entry in desc_list:
            if isinstance(entry, dict):
                val = entry.get("value") or entry.get("description") or ""
                if val:
                    description = val
                    break
            elif isinstance(entry, str) and entry:
                description = entry
                break
    feed["description"] = description

    # Brand.
    feed["brand"] = rec.get("canonicalBrand") or rec.get("brand") or ""

    # Categories – join the list with > to form a taxonomy path.
    cats = rec.get("primaryCategories") or rec.get("categories") or []
    if isinstance(cats, list):
        feed["product_category"] = " > ".join(cats)

    # Color / material / size can be mapped from Datafiniti lists.
    colors = rec.get("colors") or rec.get("color")
    if isinstance(colors, list):
        feed["color"] = ", ".join(colors)
    elif isinstance(colors, str):
        feed["color"] = colors

    sizes = rec.get("sizes") or rec.get("size")
    if isinstance(sizes, list):
        feed["size"] = ", ".join(sizes)
    elif isinstance(sizes, str):
        feed["size"] = sizes

    materials = rec.get("materials") or rec.get("material")
    if isinstance(materials, list):
        feed["material"] = ", ".join(materials)
    elif isinstance(materials, str):
        feed["material"] = materials

    # Images: choose first primaryImageURLs or fallback to imageURLs.
    images = rec.get("primaryImageURLs") or rec.get("imageURLs") or []
    if isinstance(images, list) and images:
        feed["image_url"] = images[0]
        if len(images) > 1:
            feed["additional_image_urls"] = ",".join(images[1:])
    elif isinstance(images, str):
        feed["image_url"] = images

    # Pricing: Datafiniti may return a list of price objects.
    price = None
    currency = None
    price_entries = rec.get("prices") or rec.get("price") or []
    if isinstance(price_entries, list) and price_entries:
        entry = price_entries[0]
        if isinstance(entry, dict):
            # amount may be named amountMin/amount or nested.
            for key in ("amountMin", "amount_max", "amount", "price"):
                if key in entry and entry[key] not in (None, ""):
                    price = str(entry[key])
                    break
            currency = entry.get("currency") or entry.get("currencyCode")
    elif isinstance(price_entries, dict):
        price = str(price_entries.get("amount")) if price_entries.get("amount") else None
        currency = price_entries.get("currency")
    elif price_entries:
        # simple numeric or string
        price = str(price_entries)

    if price:
        if currency:
            feed["price"] = f"{price} {currency}"
        else:
            feed["price"] = price
    # ChatGPT feed spec has separate currency column; include if available.
    if currency:
        feed["currency"] = currency

    # Product URL: use the first source URL if present.
    src_urls = rec.get("sourceURLs") or rec.get("sourceURL") or []
    if isinstance(src_urls, list) and src_urls:
        feed["url"] = src_urls[0]
    elif isinstance(src_urls, str):
        feed["url"] = src_urls

    # Seller / merchant fields.
    if seller_name:
        feed["seller_name"] = seller_name


    # Optionally merge in enrichment data.  Only override known fields that are
    # currently empty.  Unknown keys from the enrichment payload are ignored to
    # avoid introducing non‑spec attributes into the feed.
    if enrich:
        for key, value in enrich.items():
            if not value:
                continue
            # Only merge simple scalar types for fields that already exist and are empty.
            if isinstance(value, (str, int, float)):
                if key in feed and (feed[key] is None or feed[key] == ""):
                    feed[key] = str(value)

    return feed


def write_feed(
    feed_records: Iterable[Dict[str, Any]],
    output_file: str,
    compress: bool = False,
    fmt: str = "jsonl",
) -> None:
    """Write the feed records to a file as JSONL or CSV.

    Args:
        feed_records: An iterable of feed dictionaries.
        output_file: Target path to write.  When ``compress`` is True the file
            will be gzip‑compressed.
        compress: If True, gzip the output.
        fmt: "jsonl" for newline‑delimited JSON or "csv" for CSV output.

    Raises:
        ValueError: If an unsupported format is specified.
    """
    supported = {"jsonl", "csv"}
    fmt = fmt.lower()
    if fmt not in supported:
        raise ValueError(f"Unsupported feed format: {fmt}. Choose from {supported}.")

    # Determine the file handle based on compression.
    open_fn = gzip.open if compress else open  # type: ignore
    mode = "wt"  # text mode
    with open_fn(output_file, mode, encoding="utf-8") as f:
        if fmt == "jsonl":
            for record in feed_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        elif fmt == "csv":
            # Collect all keys across records to build header.
            records = list(feed_records)
            if not records:
                return
            fieldnames = sorted({k for rec in records for k in rec.keys()})
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in records:
                writer.writerow(rec)


__all__ = [
    "DATAFINITI_FETCH_FORMAT",
    "DEFAULT_POLL_SECONDS",
    "LOG_FORMAT",
    "POLL_INTERVAL_SECONDS",
    "convert_record_to_feed",
    "datafiniti_search",
    "load_env_file",
    "smartersorting_enrich",
    "write_feed",
]
