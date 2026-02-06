#!/usr/bin/env python3
"""Utilities for retrieving product data from Datafiniti, optionally enriching it
via SmarterSorting and converting the result into the official ChatGPT
product feed format.

This module can be run as a stand‑alone script or imported as a library.  It is
intended to provide a simple command‑line experience for retailers and brands
who wish to use Datafiniti product data as the foundation for the agentic
shopping benchmark and for feeding their catalog to the ChatGPT Commerce API.

The high‑level workflow is:

1. Perform a search against the Datafiniti product API using your API key and
   boolean query parameters.  You can specify the number of records to
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

The script avoids external dependencies and uses only the Python standard
library so that it can run in constrained environments.  When interacting with
external services, the script will print informative error messages instead
of crashing.

Example usage:

```bash
python datafiniti_integration/datafiniti_to_openai_feed.py \
  --datafiniti-api-key YOUR_DATAFINITI_TOKEN \
  --query "categories:shoes AND categories:women" \
  --num-records 50 \
  --output-file my_feed.jsonl

# With enrichment enabled:
python datafiniti_integration/datafiniti_to_openai_feed.py \
  --datafiniti-api-key YOUR_DATAFINITI_TOKEN \
  --smartersorting-api-key YOUR_SMARTERSORTING_TOKEN \
  --enrich \
  --query "gtins:*" \
  --num-records 10 \
  --output-file feed_with_enrichment.jsonl.gz
```

See `README.md` for detailed instructions.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

# Base URLs for Datafiniti and SmarterSorting.
DATAFINITI_SEARCH_URL = "https://api.datafiniti.co/v4/products/search"
DATAFINITI_DOWNLOAD_URL = "https://api.datafiniti.co/v4/downloads/{id}"
SMARTERSORTING_URL = "https://ui-enrichment-service-api-production-905356271911.us-central1.run.app/api/enrich_public"


def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 60) -> Dict[str, Any]:
    """Send a JSON POST request and return the parsed JSON body.

    Args:
        url: The fully qualified endpoint.
        payload: Data to JSON‑encode and send in the request body.
        headers: Additional headers such as Authorization and Content‑Type.
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        Parsed JSON response.

    Raises:
        RuntimeError: If the response cannot be decoded as JSON or a HTTP error occurs.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read()
    except urllib.error.HTTPError as e:
        # Attempt to decode the error body for a human readable message.
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = ""
        raise RuntimeError(f"HTTP {e.code} error when calling {url}: {error_body}".strip()) from e
    except Exception as e:
        raise RuntimeError(f"Network error when calling {url}: {e}") from e
    try:
        return json.loads(resp_body.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid JSON response from {url}") from exc


def datafiniti_search(
    api_key: str,
    query: str,
    num_records: Optional[int] = None,
    view: Optional[str] = None,
    download: bool = False,
    fmt: str = "JSON",
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
    resp_json = _http_post_json(DATAFINITI_SEARCH_URL, payload, headers)

    # Non‑download search returns data immediately.
    if not download:
        records = resp_json.get("records") or []
        if not isinstance(records, list):
            raise RuntimeError("Unexpected response structure: expected 'records' to be a list.")
        return records, None

    # Download flow: poll until status=completed.
    download_id = str(resp_json.get("id") or resp_json.get("_id") or resp_json.get("id"))  # handle both fields
    if not download_id:
        raise RuntimeError("No download ID returned from Datafiniti.")

    # Poll for completion.
    poll_url = DATAFINITI_DOWNLOAD_URL.format(id=download_id)
    for attempt in range(30):
        try:
            # GET request – use urllib directly
            req = urllib.request.Request(poll_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            time.sleep(2)
            continue
        status = body.get("status", "").lower()
        if status == "completed":
            break
        time.sleep(2)
    else:
        raise RuntimeError(f"Download {download_id} did not complete in time.")

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
                    except Exception:
                        continue
        except Exception as exc:
            raise RuntimeError(f"Failed to download results from {url}: {exc}") from exc
    return records, download_id


def smartersorting_enrich(
    api_key: str,
    upc: str,
    product_name: Optional[str] = None,
    user_id: Optional[str] = None,
    enable_async_enrichment: bool = False,
    re_enrich: Optional[bool] = None,
) -> Dict[str, Any]:
    """Call the SmarterSorting enrichment API for a single UPC.

    Args:
        api_key: Your SmarterSorting API token.
        upc: The UPC/GTIN of the product to enrich.
        product_name: Optional product name to assist enrichment.
        user_id: Optional user identifier for caching.
        enable_async_enrichment: Switch to asynchronous enrichment mode.
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
    return _http_post_json(SMARTERSORTING_URL, payload, headers)


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

    # Unique item identifier.  Prefer Datafiniti id, fallback to first key.
    feed["item_id"] = rec.get("id") or (rec.get("keys") or [""])[0]

    # Identifiers: GTIN/UPC/EAN.
    gtins = None
    for field in ("gtins", "upc", "ean", "ean13", "ean8", "upc", "upca", "upce"):
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


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command‑line arguments for the script."""
    parser = argparse.ArgumentParser(description="Retrieve Datafiniti products, optionally enrich, and output a ChatGPT feed.")
    parser.add_argument("--datafiniti-api-key", required=True, help="Datafiniti API token.")
    parser.add_argument("--smartersorting-api-key", help="SmarterSorting enrichment API token (optional). If provided, enrichment will be attempted when --enrich is set.")
    parser.add_argument("--openai-api-key", help="OpenAI API key (optional, not used directly by this script).")
    parser.add_argument("--query", required=True, help="Datafiniti query string. See Datafiniti docs for syntax.")
    parser.add_argument("--num-records", type=int, default=10, help="Maximum number of records to fetch (default: 10). For bulk download specify larger value and add --download.")
    parser.add_argument("--view", default=None, help="Optional Datafiniti view (e.g. product_flat_prices).")
    parser.add_argument("--download", action="store_true", help="Initiate a bulk download instead of a preview search.")
    parser.add_argument("--enrich", action="store_true", help="Enable SmarterSorting enrichment (requires --smartersorting-api-key).")
    parser.add_argument("--seller-name", default=None, help="Optional seller or retailer name to include in the feed.")
    parser.add_argument("--output-file", required=True, help="Path to write the output feed (JSONL or CSV). Use .gz extension to enable compression.")
    parser.add_argument("--format", default="jsonl", choices=["jsonl", "csv"], help="Output feed format (jsonl or csv). Default: jsonl.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    # Determine compression from filename.
    compress = args.output_file.endswith(".gz")

    # Fetch products from Datafiniti.
    print(f"Querying Datafiniti for '{args.query}' ...", file=sys.stderr)
    records, download_id = datafiniti_search(
        api_key=args.datafiniti_api_key,
        query=args.query,
        num_records=args.num_records,
        view=args.view,
        download=args.download,
        fmt="JSON" if args.format == "jsonl" else "CSV",
    )
    print(f"Retrieved {len(records)} record(s) from Datafiniti.", file=sys.stderr)
    if args.download and download_id:
        print(f"Download job ID: {download_id}", file=sys.stderr)

    # Prepare feed records.
    feed_records: List[Dict[str, Any]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        enrich_payload: Optional[Dict[str, Any]] = None
        if args.enrich:
            upc = rec.get("upc") or (rec.get("gtins") or [None])[0]
            if upc and args.smartersorting_api_key:
                try:
                    enrich_payload = smartersorting_enrich(
                        api_key=args.smartersorting_api_key,
                        upc=str(upc),
                        product_name=rec.get("name"),
                        user_id=args.seller_name,
                    )
                except Exception as exc:
                    print(f"Enrichment failed for UPC {upc}: {exc}", file=sys.stderr)
        feed_record = convert_record_to_feed(rec, enrich=enrich_payload, seller_name=args.seller_name)
        feed_records.append(feed_record)

    # Write feed to disk.
    print(f"Writing feed to {args.output_file} ...", file=sys.stderr)
    write_feed(feed_records, args.output_file, compress=compress, fmt=args.format)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    main()