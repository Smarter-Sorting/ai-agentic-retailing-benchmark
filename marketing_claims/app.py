"""Marketing Claims Product Truth Evaluation Suite - Flask Application."""

import csv
import io
import json
import logging
import os

from flask import Flask, jsonify, render_template, request, send_file

from claims_prompt import DEFAULT_CLAIMS_PROMPT, build_evaluation_prompt
from enrichment_client import enrich_product, enrich_product_by_name
from llm_client import (
    evaluate_with_anthropic,
    evaluate_with_gemini,
    parse_llm_response,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main evaluation UI."""
    return render_template("index.html", default_prompt=DEFAULT_CLAIMS_PROMPT)


@app.route("/api/evaluate", methods=["POST"])
def evaluate_claims():
    """Evaluate marketing claims for a batch of products.

    Expects JSON body:
    {
        "products": [{"upc": "...", "product_name": "...", "marketing_claims": "..."}],
        "llm_provider": "anthropic" | "gemini",
        "llm_api_key": "...",
        "enrichment_auth_token": "...",
        "enrichment_base_url": "..." (optional),
        "evaluation_prompt": "..." (optional, overrides default)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    products = data.get("products", [])
    if not products:
        return jsonify({"error": "No products provided"}), 400

    llm_provider = data.get("llm_provider", "anthropic")
    llm_api_key = data.get("llm_api_key", "")
    enrichment_token = data.get("enrichment_auth_token", "")
    enrichment_base = data.get("enrichment_base_url")
    custom_prompt = data.get("evaluation_prompt")

    if not llm_api_key:
        return jsonify({"error": "LLM API key is required"}), 400

    results = []
    for product in products:
        result = _evaluate_single_product(
            product=product,
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            enrichment_token=enrichment_token,
            enrichment_base=enrichment_base,
            custom_prompt=custom_prompt,
        )
        results.append(result)

    # Compute aggregate statistics
    stats = _compute_statistics(results)

    return jsonify({"results": results, "statistics": stats})


@app.route("/api/download-improved", methods=["POST"])
def download_improved():
    """Generate and download a CSV of improved marketing claims.

    Expects JSON body with the results array from /api/evaluate.
    """
    data = request.get_json()
    if not data or "results" not in data:
        return jsonify({"error": "Results data is required"}), 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "upc", "product_name", "original_claims", "overall_verdict",
        "overall_grade", "improved_claims", "conversion_boost_estimate",
        "claim_details",
    ])

    for r in data["results"]:
        analysis = r.get("analysis") or {}
        improvement = analysis.get("marketing_improvement_suggestions", {})
        report = analysis.get("report_card", {})
        conversion = improvement.get("conversion_impact_assessment", {})

        claims_detail = ""
        for claim in analysis.get("claims_analysis", []):
            claims_detail += (
                f"[{claim.get('verdict', 'N/A')}] {claim.get('original_claim', '')}: "
                f"{claim.get('reasoning', '')}\n"
            )

        writer.writerow([
            r.get("upc", ""),
            r.get("product_name", ""),
            r.get("marketing_claims", ""),
            analysis.get("overall_verdict", "N/A"),
            report.get("overall_grade", "N/A"),
            improvement.get("improved_claims_text", ""),
            f"{conversion.get('estimated_conversion_boost_percent', 0)}%",
            claims_detail.strip(),
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="improved_marketing_claims.csv",
    )


@app.route("/api/sample-data")
def sample_data():
    """Return the built-in sample dataset."""
    sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_products.csv")
    products = []
    try:
        with open(sample_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append({
                    "upc": row.get("upc", ""),
                    "product_name": row.get("product_name", ""),
                    "marketing_claims": row.get("marketing_claims", ""),
                })
    except FileNotFoundError:
        return jsonify({"error": "Sample data file not found"}), 404

    return jsonify({"products": products})


@app.route("/api/prompt")
def get_prompt():
    """Return the default evaluation prompt template."""
    return jsonify({"prompt": DEFAULT_CLAIMS_PROMPT})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _evaluate_single_product(product, llm_provider, llm_api_key,
                             enrichment_token, enrichment_base, custom_prompt):
    """Run the full evaluation pipeline for one product."""
    upc = product.get("upc", "").strip()
    product_name = product.get("product_name", "").strip()
    marketing_claims = product.get("marketing_claims", "").strip()

    # Step 1: Enrich via SmarterSorting
    enrichment_data = {}
    enrichment_error = None
    if enrichment_token:
        if upc:
            enrich_result = enrich_product(upc, enrichment_token, enrichment_base)
        else:
            enrich_result = enrich_product_by_name(product_name, enrichment_token, enrichment_base)

        if enrich_result.get("success"):
            enrichment_data = enrich_result["data"]
        else:
            enrichment_error = enrich_result.get("error", "Unknown enrichment error")
    else:
        enrichment_error = "No enrichment auth token provided — evaluation based on claims text only"

    # Step 2: Build prompt
    enrichment_text = json.dumps(enrichment_data, indent=2) if enrichment_data else "No enrichment data available — evaluate claims based on general product knowledge and the product name."

    if custom_prompt:
        prompt = custom_prompt.format(
            upc=upc,
            product_name=product_name,
            marketing_claims=marketing_claims,
            enrichment_data=enrichment_text,
        )
    else:
        prompt = build_evaluation_prompt(upc, product_name, marketing_claims, enrichment_text)

    # Step 3: Call LLM
    if llm_provider == "gemini":
        llm_result = evaluate_with_gemini(prompt, llm_api_key)
    else:
        llm_result = evaluate_with_anthropic(prompt, llm_api_key)

    # Step 4: Parse response
    analysis = None
    llm_error = None
    if llm_result.get("success"):
        analysis = parse_llm_response(llm_result["text"])
        if not analysis:
            llm_error = "Failed to parse LLM response as JSON"
    else:
        llm_error = llm_result.get("error", "Unknown LLM error")

    # Build base response payload (fields used by the frontend)
    response = {
        "upc": upc,
        "product_name": product_name,
        "marketing_claims": marketing_claims,
        "enrichment_error": enrichment_error,
        "analysis": analysis,
        "llm_error": llm_error,
    }

    # Optionally include large/sensitive debugging fields if explicitly requested.
    include_debug = False
    try:
        # Prefer an explicit flag in the JSON body (e.g., {"debug": true})
        payload = request.get_json(silent=True) or {}
        include_debug = bool(
            payload.get("debug")
            or payload.get("include_debug")
            or request.args.get("debug")
            or request.args.get("include_debug")
        )
    except Exception:
        # If anything goes wrong determining debug mode, fall back to safe default.
        include_debug = False

    if include_debug:
        response["enrichment_data"] = enrichment_data
        response["llm_raw_text"] = llm_result.get("text", "") if llm_result.get("success") else ""

    return response
def _compute_statistics(results):
    """Compute aggregate statistics from evaluation results."""
    total = len(results)
    verdicts = {"VALID": 0, "INVALID": 0, "PARTIALLY_VALID": 0, "ERROR": 0}
    claim_categories = {}
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    valid_claim_words = {}
    invalid_claim_words = {}
    all_claims = []
    total_conversion_boost = 0
    conversion_count = 0

    for r in results:
        analysis = r.get("analysis")
        if not analysis:
            verdicts["ERROR"] += 1
            continue

        verdict = analysis.get("overall_verdict", "ERROR")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

        # Claim categories
        for claim in analysis.get("claims_analysis", []):
            cat = claim.get("claim_category", "Unknown")
            claim_categories[cat] = claim_categories.get(cat, 0) + 1
            all_claims.append(claim)

            # Word frequency for word clouds
            words = claim.get("original_claim", "").lower().split()
            word_dict = valid_claim_words if claim.get("verdict") == "VALID" else invalid_claim_words
            for word in words:
                clean = word.strip(".,;:!?\"'()[]")
                if len(clean) > 3:
                    word_dict[clean] = word_dict.get(clean, 0) + 1

        # Report card grades
        report = analysis.get("report_card", {})
        grade = report.get("overall_grade", "")
        if grade in grades:
            grades[grade] += 1

        # Conversion boost
        improvement = analysis.get("marketing_improvement_suggestions", {})
        conv = improvement.get("conversion_impact_assessment", {})
        boost = conv.get("estimated_conversion_boost_percent", 0)
        if isinstance(boost, (int, float)):
            total_conversion_boost += boost
            conversion_count += 1

    avg_boost = round(total_conversion_boost / conversion_count, 1) if conversion_count else 0

    # Ingredient-to-claim network data
    ingredient_claim_links = []
    for r in results:
        analysis = r.get("analysis")
        if not analysis:
            continue
        ingredients = (analysis.get("product_truth_summary") or {}).get("key_ingredients", [])
        for claim in analysis.get("claims_analysis", []):
            cat = claim.get("claim_category", "Unknown")
            for ing in ingredients:
                ingredient_claim_links.append({"source": ing, "target": cat})

    return {
        "total_products": total,
        "verdicts": verdicts,
        "claim_categories": claim_categories,
        "grades": grades,
        "valid_claim_words": dict(sorted(valid_claim_words.items(), key=lambda x: -x[1])[:50]),
        "invalid_claim_words": dict(sorted(invalid_claim_words.items(), key=lambda x: -x[1])[:50]),
        "average_conversion_boost": avg_boost,
        "ingredient_claim_links": ingredient_claim_links,
        "total_claims_evaluated": len(all_claims),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
