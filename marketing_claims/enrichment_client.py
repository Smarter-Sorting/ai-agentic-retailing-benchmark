"""Client for the SmarterSorting Enrichment API.

Uses the POST /api/enrich_public endpoint as documented in the
datafiniti_integration module to enrich products either by UPC
(via ``enrich_product``) or by product name when a UPC is not
available (via ``enrich_product_by_name``).
"""

import json
import logging
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://ui-enrichment-service-api-production-905356271911.us-central1.run.app"


def enrich_product(upc, auth_token, base_url=None, product_name=None):
    """Fetch enrichment data for a product by UPC via POST /api/enrich_public.

    Args:
        upc: The product UPC code.
        auth_token: Bearer token for authentication.
        base_url: Optional override for the enrichment API base URL.
        product_name: Optional product name to assist enrichment.

    Returns:
        dict with enrichment data or error information.
    """
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    url = f"{base}/api/enrich_public"

    auth_value = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_value,
    }

    payload = {"upc": str(upc)}
    if product_name:
        payload["product_name"] = product_name

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        logger.warning("Enrichment API error %s for UPC %s: %s", exc.code, upc, detail)
        return {"success": False, "error": f"HTTP {exc.code}: {detail}", "status_code": exc.code}
    except urllib.error.URLError as exc:
        logger.warning("Enrichment API connection error for UPC %s: %s", upc, exc.reason)
        return {"success": False, "error": f"Connection error: {exc.reason}"}
    except Exception as exc:
        logger.warning("Enrichment API unexpected error for UPC %s: %s", upc, exc)
        return {"success": False, "error": str(exc)}


def enrich_product_by_name(product_name, auth_token, base_url=None):
    """Enrich a product by name when UPC is not available.

    Uses the same POST endpoint with product_name only.

    Args:
        product_name: The product name to search for.
        auth_token: Bearer token for authentication.
        base_url: Optional override for the enrichment API base URL.

    Returns:
        dict with enrichment data or error information.
    """
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    url = f"{base}/api/enrich_public"

    auth_value = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_value,
    }

    payload = {"product_name": str(product_name)}
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        logger.warning("Enrichment search error %s for '%s': %s", exc.code, product_name, detail)
        return {"success": False, "error": f"HTTP {exc.code}: {detail}", "status_code": exc.code}
    except urllib.error.URLError as exc:
        logger.warning("Enrichment search connection error for '%s': %s", product_name, exc.reason)
        return {"success": False, "error": f"Connection error: {exc.reason}"}
    except Exception as exc:
        logger.warning("Enrichment search unexpected error for '%s': %s", product_name, exc)
        return {"success": False, "error": str(exc)}
