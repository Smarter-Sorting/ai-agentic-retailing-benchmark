"""Unit tests for the Datafiniti to ChatGPT feed converter.

These tests exercise the core mapping logic in ``convert_record_to_feed``.  They do not
hit external services and are safe to run without network access.
"""

import unittest

from datafiniti_integration.datafiniti_to_openai_feed import convert_record_to_feed


class ConvertRecordToFeedTest(unittest.TestCase):
    def test_basic_conversion(self):
        """Ensure that a minimal Datafiniti record is converted into a feed entry."""
        rec = {
            "id": "ABC123",
            "name": "Sample Product",
            "brand": "TestBrand",
            "gtins": ["012345678905"],
            "categories": ["Electronics", "Computers"],
            "imageURLs": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
            "prices": [
                {
                    "amount": 99.99,
                    "currency": "USD",
                }
            ],
            "sourceURLs": ["https://example.com/product/ABC123"],
        }
        feed = convert_record_to_feed(rec, enrich=None, seller_name="MyStore")
        self.assertEqual(feed["item_id"], "ABC123")
        self.assertEqual(feed["title"], "Sample Product")
        self.assertEqual(feed["brand"], "TestBrand")
        self.assertEqual(feed["gtin"], "012345678905")
        self.assertEqual(feed["product_category"], "Electronics > Computers")
        self.assertEqual(feed["price"], "99.99 USD")
        self.assertEqual(feed["url"], "https://example.com/product/ABC123")
        self.assertEqual(feed["image_url"], "https://example.com/image1.jpg")
        self.assertEqual(feed["seller_name"], "MyStore")
        # Eligibility flags should be set to strings
        self.assertEqual(feed["is_eligible_search"], "true")
        self.assertEqual(feed["is_eligible_checkout"], "false")

    def test_enrichment_overrides(self):
        """Verify that enrichment values override base record fields when missing."""
        rec = {
            "id": "DEF456",
            "name": "Plain Product",
            "brand": "",
            "gtins": ["000111222333"],
            "categories": ["Home"],
            "prices": [
                {
                    "amount": 10.0,
                    "currency": "USD",
                }
            ],
            "sourceURLs": ["https://example.com/product/DEF456"],
        }
        enrich = {
            "brand": "EnrichedBrand",
            "canonicalDescription": "Enriched description text",
        }
        feed = convert_record_to_feed(rec, enrich=enrich, seller_name=None)
        # Brand should be filled from enrichment because base was empty
        self.assertEqual(feed["brand"], "EnrichedBrand")
        # Unknown enrichment keys should be ignored and not appear in the feed
        self.assertNotIn("canonicalDescription", feed)
        # Base description remains empty because enrichment does not override unknown fields
        self.assertEqual(feed.get("description"), "")


if __name__ == "__main__":
    unittest.main()