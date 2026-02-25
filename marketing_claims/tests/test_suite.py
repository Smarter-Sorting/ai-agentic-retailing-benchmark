"""Comprehensive test suite for the Marketing Claims Product Truth Evaluation Suite.

Tests all components with stubbed API responses:
- CSV parsing and product loading
- Enrichment client
- LLM client (Anthropic & Gemini)
- Claims prompt building
- Flask API endpoints
- Statistics computation
- Download generation
"""

import csv
import io
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory and tests directory to path
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_tests_dir)
sys.path.insert(0, _parent_dir)
sys.path.insert(0, _tests_dir)

from stub_responses import (
    ENRICHMENT_STUBS,
    LLM_ANALYSIS_STUBS,
    get_stub_enrichment,
    get_stub_llm_response,
    get_stub_claude_api_response,
    get_stub_gemini_api_response,
)


class TestClaimsPrompt(unittest.TestCase):
    """Test the claims evaluation prompt building."""

    def test_build_evaluation_prompt(self):
        from claims_prompt import build_evaluation_prompt
        prompt = build_evaluation_prompt(
            upc="041100001214",
            product_name="Coppertone Sport Sunscreen SPF 50",
            marketing_claims="Broad spectrum UVA/UVB protection. Water resistant.",
            enrichment_data='{"ingredients": ["Avobenzone 3%"]}',
        )
        self.assertIn("041100001214", prompt)
        self.assertIn("Coppertone", prompt)
        self.assertIn("Broad spectrum", prompt)
        self.assertIn("Avobenzone", prompt)
        self.assertIn("FTC Act Section 5", prompt)
        self.assertIn("FDA", prompt)

    def test_default_prompt_has_all_categories(self):
        from claims_prompt import DEFAULT_CLAIMS_PROMPT
        categories = [
            "Efficacy Claim", "Safety Claim", "Ingredient Claim",
            "Environmental Claim", "Certification Claim", "Comparative Claim",
            "Consumer Perception Claim", "Regulatory Claim", "Natural/Organic Claim",
            "Performance Claim",
        ]
        for cat in categories:
            self.assertIn(cat, DEFAULT_CLAIMS_PROMPT, f"Missing category: {cat}")

    def test_prompt_has_output_format(self):
        from claims_prompt import DEFAULT_CLAIMS_PROMPT
        self.assertIn("overall_verdict", DEFAULT_CLAIMS_PROMPT)
        self.assertIn("claims_analysis", DEFAULT_CLAIMS_PROMPT)
        self.assertIn("report_card", DEFAULT_CLAIMS_PROMPT)
        self.assertIn("marketing_improvement_suggestions", DEFAULT_CLAIMS_PROMPT)


class TestEnrichmentClient(unittest.TestCase):
    """Test the enrichment client with mocked HTTP calls."""

    @patch("enrichment_client.urllib.request.urlopen")
    def test_enrich_product_success(self, mock_urlopen):
        from enrichment_client import enrich_product

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            ENRICHMENT_STUBS["041100001214"]
        ).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = enrich_product("041100001214", "test-token")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["canonicalBrand"], "Coppertone")

    @patch("enrichment_client.urllib.request.urlopen")
    def test_enrich_product_http_error(self, mock_urlopen):
        from enrichment_client import enrich_product
        import urllib.error

        error = urllib.error.HTTPError(
            url="http://test",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b"Invalid token"),
        )
        mock_urlopen.side_effect = error

        result = enrich_product("041100001214", "bad-token")
        self.assertFalse(result["success"])
        self.assertIn("401", result["error"])

    @patch("enrichment_client.urllib.request.urlopen")
    def test_enrich_product_connection_error(self, mock_urlopen):
        from enrichment_client import enrich_product
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = enrich_product("041100001214", "test-token")
        self.assertFalse(result["success"])
        self.assertIn("Connection error", result["error"])

    @patch("enrichment_client.urllib.request.urlopen")
    def test_enrich_sends_post_with_upc(self, mock_urlopen):
        from enrichment_client import enrich_product

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"upc": "123"}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        enrich_product("123", "tok")

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        self.assertEqual(req.method, "POST")
        self.assertIn("/api/enrich_public", req.full_url)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["upc"], "123")


class TestLLMClient(unittest.TestCase):
    """Test the LLM client with mocked HTTP calls."""

    @patch("llm_client.urllib.request.urlopen")
    def test_anthropic_success(self, mock_urlopen):
        from llm_client import evaluate_with_anthropic

        api_response = get_stub_claude_api_response("041100001214")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = evaluate_with_anthropic("test prompt", "test-key")
        self.assertTrue(result["success"])
        self.assertIn("overall_verdict", result["text"])

    @patch("llm_client.urllib.request.urlopen")
    def test_gemini_success(self, mock_urlopen):
        from llm_client import evaluate_with_gemini

        api_response = get_stub_gemini_api_response("041100001214")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = evaluate_with_gemini("test prompt", "test-key")
        self.assertTrue(result["success"])
        self.assertIn("overall_verdict", result["text"])

    @patch("llm_client.urllib.request.urlopen")
    def test_anthropic_http_error(self, mock_urlopen):
        from llm_client import evaluate_with_anthropic
        import urllib.error

        error = urllib.error.HTTPError(
            url="http://test", code=429, msg="Rate limited",
            hdrs={}, fp=io.BytesIO(b"Too many requests"),
        )
        mock_urlopen.side_effect = error

        result = evaluate_with_anthropic("test", "test-key")
        self.assertFalse(result["success"])
        self.assertIn("429", result["error"])

    def test_parse_llm_response_valid_json(self):
        from llm_client import parse_llm_response
        data = '{"overall_verdict": "VALID"}'
        result = parse_llm_response(data)
        self.assertIsNotNone(result)
        self.assertEqual(result["overall_verdict"], "VALID")

    def test_parse_llm_response_markdown_wrapped(self):
        from llm_client import parse_llm_response
        data = '```json\n{"overall_verdict": "INVALID"}\n```'
        result = parse_llm_response(data)
        self.assertIsNotNone(result)
        self.assertEqual(result["overall_verdict"], "INVALID")

    def test_parse_llm_response_with_preamble(self):
        from llm_client import parse_llm_response
        data = 'Here is the analysis:\n{"overall_verdict": "VALID"}'
        result = parse_llm_response(data)
        self.assertIsNotNone(result)
        self.assertEqual(result["overall_verdict"], "VALID")

    def test_parse_llm_response_empty(self):
        from llm_client import parse_llm_response
        self.assertIsNone(parse_llm_response(""))
        self.assertIsNone(parse_llm_response(None))

    def test_parse_llm_response_invalid(self):
        from llm_client import parse_llm_response
        self.assertIsNone(parse_llm_response("This is not JSON at all"))


class TestStubResponses(unittest.TestCase):
    """Test stub response data integrity."""

    def test_enrichment_stubs_have_required_fields(self):
        for upc, data in ENRICHMENT_STUBS.items():
            self.assertIn("upc", data)
            self.assertIn("canonicalBrand", data)
            self.assertIn("ingredients", data)
            self.assertIsInstance(data["ingredients"], list)

    def test_llm_analysis_stubs_have_required_fields(self):
        for upc, analysis in LLM_ANALYSIS_STUBS.items():
            self.assertIn("overall_verdict", analysis)
            self.assertIn("claims_analysis", analysis)
            self.assertIn("report_card", analysis)
            self.assertIn("marketing_improvement_suggestions", analysis)
            self.assertIn(analysis["overall_verdict"], ["VALID", "INVALID", "PARTIALLY_VALID"])

    def test_claims_have_verdicts(self):
        valid_verdicts = {"VALID", "INVALID", "NEEDS_SUBSTANTIATION", "MISLEADING"}
        for upc, analysis in LLM_ANALYSIS_STUBS.items():
            for claim in analysis["claims_analysis"]:
                self.assertIn("original_claim", claim)
                self.assertIn("verdict", claim)
                self.assertIn(claim["verdict"], valid_verdicts,
                              f"Invalid verdict '{claim['verdict']}' for {upc}")

    def test_report_cards_have_valid_grades(self):
        valid_grades = {"A", "B", "C", "D", "F"}
        for upc, analysis in LLM_ANALYSIS_STUBS.items():
            report = analysis["report_card"]
            for key, grade in report.items():
                self.assertIn(grade, valid_grades,
                              f"Invalid grade '{grade}' for {key} in {upc}")


class TestFlaskApp(unittest.TestCase):
    """Test Flask application routes with stubbed responses."""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Marketing Claims Product Truth Evaluation Suite", resp.data)
        self.assertIn(b"PapaParse", resp.data)
        self.assertIn(b"Chart.js", resp.data)

    def test_sample_data_endpoint(self):
        resp = self.client.get("/api/sample-data")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("products", data)
        self.assertGreater(len(data["products"]), 0)
        # Check structure
        product = data["products"][0]
        self.assertIn("upc", product)
        self.assertIn("product_name", product)
        self.assertIn("marketing_claims", product)

    def test_prompt_endpoint(self):
        resp = self.client.get("/api/prompt")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("prompt", data)
        self.assertIn("FTC", data["prompt"])

    def test_evaluate_no_body(self):
        resp = self.client.post("/api/evaluate",
                                content_type="application/json")
        self.assertIn(resp.status_code, (400, 415))

    def test_evaluate_no_products(self):
        resp = self.client.post("/api/evaluate",
                                json={"products": [], "llm_api_key": "key"})
        self.assertEqual(resp.status_code, 400)

    def test_evaluate_no_api_key(self):
        resp = self.client.post("/api/evaluate", json={
            "products": [{"upc": "123", "product_name": "Test", "marketing_claims": "Great"}],
            "llm_provider": "anthropic",
            "llm_api_key": "",
        })
        self.assertEqual(resp.status_code, 400)

    @patch("app.evaluate_with_anthropic")
    @patch("app.enrich_product")
    def test_evaluate_full_pipeline(self, mock_enrich, mock_llm):
        """Test the full evaluation pipeline with stubbed responses."""
        mock_enrich.return_value = get_stub_enrichment("041100001214")
        mock_llm.return_value = get_stub_llm_response("041100001214")

        resp = self.client.post("/api/evaluate", json={
            "products": [{
                "upc": "041100001214",
                "product_name": "Coppertone Sport Sunscreen SPF 50",
                "marketing_claims": "Broad spectrum UVA/UVB protection. Water resistant (80 minutes).",
            }],
            "llm_provider": "anthropic",
            "llm_api_key": "test-key-123",
            "enrichment_auth_token": "test-enrich-token",
        })

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("results", data)
        self.assertIn("statistics", data)
        self.assertEqual(len(data["results"]), 1)

        result = data["results"][0]
        self.assertIn("analysis", result)
        self.assertIsNotNone(result["analysis"])
        self.assertIn("overall_verdict", result["analysis"])

    @patch("app.evaluate_with_anthropic")
    @patch("app.enrich_product")
    def test_evaluate_multiple_products(self, mock_enrich, mock_llm):
        """Test evaluation with multiple products."""
        def enrich_side_effect(upc, token, base=None):
            return get_stub_enrichment(upc)

        def llm_side_effect(prompt, api_key, model=None):
            for upc in ["041100001214", "037000711209", "381370044307"]:
                if upc in prompt:
                    return get_stub_llm_response(upc)
            return get_stub_llm_response("unknown")

        mock_enrich.side_effect = enrich_side_effect
        mock_llm.side_effect = llm_side_effect

        products = [
            {"upc": "041100001214", "product_name": "Coppertone SPF 50", "marketing_claims": "Broad spectrum."},
            {"upc": "037000711209", "product_name": "Tide Original", "marketing_claims": "#1 detergent."},
            {"upc": "381370044307", "product_name": "Aveeno Lotion", "marketing_claims": "24 hour moisture."},
        ]

        resp = self.client.post("/api/evaluate", json={
            "products": products,
            "llm_provider": "anthropic",
            "llm_api_key": "test-key",
            "enrichment_auth_token": "test-token",
        })

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["results"]), 3)
        self.assertIn("statistics", data)
        stats = data["statistics"]
        self.assertEqual(stats["total_products"], 3)
        self.assertGreater(stats["total_claims_evaluated"], 0)

    @patch("app.evaluate_with_anthropic")
    @patch("app.enrich_product")
    def test_evaluate_without_enrichment_token(self, mock_enrich, mock_llm):
        """Test evaluation works without enrichment credentials."""
        mock_llm.return_value = get_stub_llm_response("041100001214")

        resp = self.client.post("/api/evaluate", json={
            "products": [{
                "upc": "041100001214",
                "product_name": "Coppertone SPF 50",
                "marketing_claims": "Broad spectrum protection.",
            }],
            "llm_provider": "anthropic",
            "llm_api_key": "test-key",
        })

        self.assertEqual(resp.status_code, 200)
        mock_enrich.assert_not_called()  # Should not call enrichment without token
        data = resp.get_json()
        result = data["results"][0]
        self.assertIn("enrichment_error", result)

    @patch("app.evaluate_with_gemini")
    @patch("app.enrich_product")
    def test_evaluate_with_gemini(self, mock_enrich, mock_llm):
        """Test evaluation with Gemini provider."""
        mock_enrich.return_value = get_stub_enrichment("041100001214")
        mock_llm.return_value = get_stub_llm_response("041100001214")

        resp = self.client.post("/api/evaluate", json={
            "products": [{
                "upc": "041100001214",
                "product_name": "Coppertone SPF 50",
                "marketing_claims": "Broad spectrum.",
            }],
            "llm_provider": "gemini",
            "llm_api_key": "gemini-test-key",
            "enrichment_auth_token": "test-token",
        })

        self.assertEqual(resp.status_code, 200)
        mock_llm.assert_called_once()

    def test_download_improved_no_data(self):
        resp = self.client.post("/api/download-improved",
                                content_type="application/json")
        self.assertIn(resp.status_code, (400, 415))

    def test_download_improved_with_results(self):
        results = [{
            "upc": "041100001214",
            "product_name": "Coppertone SPF 50",
            "marketing_claims": "Broad spectrum.",
            "analysis": LLM_ANALYSIS_STUBS["041100001214"],
        }]

        resp = self.client.post("/api/download-improved",
                                json={"results": results})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.content_type)

        # Parse the CSV response
        csv_text = resp.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["upc"], "041100001214")
        self.assertIn("improved_claims", rows[0])


class TestStatisticsComputation(unittest.TestCase):
    """Test the aggregate statistics computation."""

    def test_compute_statistics(self):
        from app import _compute_statistics

        results = [
            {"analysis": LLM_ANALYSIS_STUBS["041100001214"]},
            {"analysis": LLM_ANALYSIS_STUBS["037000711209"]},
            {"analysis": LLM_ANALYSIS_STUBS["381370044307"]},
        ]

        stats = _compute_statistics(results)
        self.assertEqual(stats["total_products"], 3)
        self.assertGreater(stats["total_claims_evaluated"], 0)

        # Check verdicts
        verdicts = stats["verdicts"]
        self.assertIn("VALID", verdicts)
        self.assertIn("PARTIALLY_VALID", verdicts)

        # Check claim categories
        self.assertGreater(len(stats["claim_categories"]), 0)

        # Check grades
        self.assertGreater(len(stats["grades"]), 0)

        # Check word clouds
        self.assertIsInstance(stats["valid_claim_words"], dict)
        self.assertIsInstance(stats["invalid_claim_words"], dict)

    def test_compute_statistics_with_errors(self):
        from app import _compute_statistics

        results = [
            {"analysis": None},
            {"analysis": LLM_ANALYSIS_STUBS["041100001214"]},
        ]

        stats = _compute_statistics(results)
        self.assertEqual(stats["total_products"], 2)
        self.assertEqual(stats["verdicts"]["ERROR"], 1)


class TestSampleData(unittest.TestCase):
    """Test the sample dataset."""

    def test_sample_csv_exists(self):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_data", "sample_products.csv",
        )
        self.assertTrue(os.path.exists(sample_path))

    def test_sample_csv_has_correct_columns(self):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_data", "sample_products.csv",
        )
        with open(sample_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            self.assertIn("upc", headers)
            self.assertIn("product_name", headers)
            self.assertIn("marketing_claims", headers)

    def test_sample_csv_has_products(self):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_data", "sample_products.csv",
        )
        with open(sample_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            products = list(reader)
            self.assertGreater(len(products), 10)  # At least 10 products

    def test_sample_products_have_valid_and_invalid_claims(self):
        """Verify the sample data contains products with both types of claims."""
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_data", "sample_products.csv",
        )
        with open(sample_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            all_claims = [row["marketing_claims"] for row in reader]

        # Check for typical valid claim patterns
        all_text = " ".join(all_claims).lower()
        self.assertIn("dermatologist", all_text)
        self.assertIn("clinically proven", all_text)

        # Check for typical potentially invalid claim patterns
        has_potentially_invalid = any(
            pattern in all_text for pattern in [
                "chemical-free", "all-natural", "kills 99.9%",
                "100% natural", "#1", "hydrates better than water",
            ]
        )
        self.assertTrue(has_potentially_invalid,
                        "Sample data should include potentially invalid claims for testing")


class TestEndToEndFlow(unittest.TestCase):
    """Integration test for the complete evaluation workflow."""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.evaluate_with_anthropic")
    @patch("app.enrich_product")
    def test_full_workflow(self, mock_enrich, mock_llm):
        """Test: load sample data -> evaluate -> download."""
        # Step 1: Load sample data
        resp = self.client.get("/api/sample-data")
        self.assertEqual(resp.status_code, 200)
        products = resp.get_json()["products"]
        self.assertGreater(len(products), 0)

        # Use first 3 products
        test_products = products[:3]

        # Step 2: Setup mocks
        def enrich_side(upc, token, base=None):
            return get_stub_enrichment(upc)

        def llm_side(prompt, api_key, model=None):
            for upc in LLM_ANALYSIS_STUBS:
                if upc in prompt:
                    return get_stub_llm_response(upc)
            return get_stub_llm_response("unknown")

        mock_enrich.side_effect = enrich_side
        mock_llm.side_effect = llm_side

        # Step 3: Run evaluation
        resp = self.client.post("/api/evaluate", json={
            "products": test_products,
            "llm_provider": "anthropic",
            "llm_api_key": "test-key",
            "enrichment_auth_token": "test-token",
        })
        self.assertEqual(resp.status_code, 200)
        eval_data = resp.get_json()
        self.assertEqual(len(eval_data["results"]), 3)
        self.assertIn("statistics", eval_data)

        # Step 4: Download improved claims
        resp = self.client.post("/api/download-improved",
                                json={"results": eval_data["results"]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.content_type)


if __name__ == "__main__":
    unittest.main()
