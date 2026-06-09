"""Stubbed API responses for testing the Marketing Claims Evaluation Suite.

Provides realistic mock responses for:
- SmarterSorting Enrichment API
- Anthropic Claude API
- Google Gemini API
"""

import json

# -----------------------------------------------------------------------
# SmarterSorting Enrichment Stubs
# -----------------------------------------------------------------------

ENRICHMENT_RESPONSE_COPPERTONE = {
    "upc": "041100001214",
    "canonicalBrand": "Coppertone",
    "canonicalDescription": "Coppertone Sport Sunscreen Lotion SPF 50",
    "brand": "Coppertone",
    "productCategory": "Sunscreen",
    "ingredients": [
        "Avobenzone 3%", "Homosalate 13%", "Octisalate 5%",
        "Octocrylene 7%", "Oxybenzone 4%",
        "Water", "Sorbitol", "Styrene/Acrylates Copolymer",
        "Silica", "Beeswax", "Fragrance",
    ],
    "activeIngredients": [
        {"name": "Avobenzone", "concentration": "3%"},
        {"name": "Homosalate", "concentration": "13%"},
        {"name": "Octisalate", "concentration": "5%"},
        {"name": "Octocrylene", "concentration": "7%"},
        {"name": "Oxybenzone", "concentration": "4%"},
    ],
    "regulatoryStatus": "FDA OTC Drug (Sunscreen Monograph 21 CFR 352)",
    "ghsClassification": "Not classified as hazardous",
    "signalWord": None,
    "precautionaryStatements": [
        "For external use only",
        "Do not use on damaged or broken skin",
        "When using this product keep out of eyes",
    ],
    "certifications": [],
    "hazardStatements": [],
    "warnings": [
        "Skin cancer/skin aging alert",
        "Stop use if rash occurs",
    ],
}

ENRICHMENT_RESPONSE_TIDE = {
    "upc": "037000711209",
    "canonicalBrand": "Tide",
    "canonicalDescription": "Tide Original Liquid Laundry Detergent",
    "brand": "Tide",
    "productCategory": "Laundry Detergent",
    "ingredients": [
        "Water", "Alcohol Ethoxylate C12-15", "Linear Alkylbenzene Sulfonate",
        "Propylene Glycol", "Citric Acid", "Sodium Hydroxide",
        "Borax", "Ethanolamine", "Sodium Fatty Acids",
        "Diquaternium Ethoxy Sulfate", "Protease", "Amylase",
        "Fragrance", "Disodium Diaminostilbene Disulfonate",
        "Liquitint Blue", "CI 61585",
    ],
    "activeIngredients": [],
    "regulatoryStatus": "Consumer product — not classified as pesticide or drug",
    "ghsClassification": "Eye Irritation Category 2A, Skin Irritation Category 2",
    "signalWord": "Warning",
    "precautionaryStatements": [
        "Causes serious eye irritation",
        "Causes skin irritation",
        "Keep out of reach of children",
    ],
    "certifications": [],
    "hazardStatements": ["H319: Causes serious eye irritation", "H315: Causes skin irritation"],
    "warnings": [
        "Keep out of reach of children",
        "May cause eye and skin irritation",
    ],
}

ENRICHMENT_RESPONSE_AVEENO = {
    "upc": "381370044307",
    "canonicalBrand": "Aveeno",
    "canonicalDescription": "Aveeno Daily Moisturizing Lotion",
    "brand": "Aveeno",
    "productCategory": "Skin Moisturizer",
    "ingredients": [
        "Water", "Glycerin", "Distearyldimonium Chloride",
        "Petrolatum", "Isopropyl Palmitate", "Cetyl Alcohol",
        "Avena Sativa (Oat) Kernel Flour", "Dimethicone",
        "Benzyl Alcohol", "Sodium Chloride",
    ],
    "activeIngredients": [
        {"name": "Colloidal Oatmeal", "concentration": "1%"},
    ],
    "regulatoryStatus": "FDA OTC Drug (Skin Protectant)",
    "ghsClassification": "Not classified as hazardous",
    "signalWord": None,
    "precautionaryStatements": ["For external use only"],
    "certifications": ["National Eczema Association Seal of Acceptance"],
    "hazardStatements": [],
    "warnings": [],
}

ENRICHMENT_STUBS = {
    "041100001214": ENRICHMENT_RESPONSE_COPPERTONE,
    "037000711209": ENRICHMENT_RESPONSE_TIDE,
    "381370044307": ENRICHMENT_RESPONSE_AVEENO,
}


# -----------------------------------------------------------------------
# LLM Response Stubs — Anthropic Claude
# -----------------------------------------------------------------------

def _build_claude_response(analysis_json):
    """Wrap an analysis JSON in the Anthropic Messages API response format."""
    return {
        "id": "msg_stub_01",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "text", "text": json.dumps(analysis_json, indent=2)}
        ],
        "model": "claude-sonnet-4-6",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1500, "output_tokens": 800},
    }


ANALYSIS_COPPERTONE = {
    "product_name": "Coppertone Sport Sunscreen SPF 50",
    "upc": "041100001214",
    "overall_verdict": "PARTIALLY_VALID",
    "confidence_score": 0.85,
    "claims_analysis": [
        {
            "original_claim": "Broad spectrum UVA/UVB protection",
            "claim_category": "Regulatory Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Product contains FDA-approved broad-spectrum UV filters (avobenzone + octocrylene). SPF 50 with broad-spectrum designation is substantiated by the active ingredients.",
            "regulatory_references": ["FDA 21 CFR 352", "FDA Final Rule on Sunscreen"],
            "suggested_improvement": "Broad spectrum UVA/UVB protection",
            "evidence_from_enrichment": "Active ingredients: Avobenzone 3%, Homosalate 13%, Octisalate 5%, Octocrylene 7%",
        },
        {
            "original_claim": "Water resistant (80 minutes)",
            "claim_category": "Performance Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "FDA allows 'water resistant (80 minutes)' claim when substantiated by standard testing. This is a regulated claim for OTC sunscreens.",
            "regulatory_references": ["FDA 21 CFR 201.327"],
            "suggested_improvement": "Water resistant (80 minutes)",
            "evidence_from_enrichment": "Product is OTC drug under sunscreen monograph",
        },
        {
            "original_claim": "Non-greasy formula",
            "claim_category": "Consumer Perception Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Subjective sensory claim that falls within acceptable cosmetic puffery. However, ingredient list includes petrolatum-like compounds which some consumers may perceive as greasy.",
            "regulatory_references": ["FTC sensory claim guidance"],
            "suggested_improvement": "Lightweight, non-greasy feel",
            "evidence_from_enrichment": "Contains silica (mattifying agent)",
        },
        {
            "original_claim": "Dermatologist recommended",
            "claim_category": "Certification Claim",
            "verdict": "NEEDS_SUBSTANTIATION",
            "severity": "MEDIUM",
            "reasoning": "Requires survey data showing that a meaningful proportion of dermatologists actually recommend this product. FTC Endorsement Guides require substantiation for 'recommended by' claims.",
            "regulatory_references": ["FTC Endorsement Guides 16 CFR 255"],
            "suggested_improvement": "Trusted by dermatologists for sun protection",
            "evidence_from_enrichment": "No certification data found in enrichment for dermatologist endorsement",
        },
        {
            "original_claim": "Won't run into eyes",
            "claim_category": "Performance Claim",
            "verdict": "MISLEADING",
            "severity": "HIGH",
            "reasoning": "This is an absolute performance claim that is difficult to substantiate. The product contains chemical UV filters and fragrance that can cause significant eye irritation. Precautionary statement says 'keep out of eyes'.",
            "regulatory_references": ["FTC Act Section 5", "21 CFR 352"],
            "suggested_improvement": "Designed to resist running into eyes during activity",
            "evidence_from_enrichment": "Precautionary: 'When using this product keep out of eyes'",
        },
        {
            "original_claim": "Clinically proven sun protection",
            "claim_category": "Efficacy Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "As an FDA-regulated OTC drug, SPF testing is required. The claim is substantiated by mandatory clinical SPF testing under FDA monograph.",
            "regulatory_references": ["FDA 21 CFR 352 SPF testing requirements"],
            "suggested_improvement": "Clinically proven sun protection",
            "evidence_from_enrichment": "FDA OTC Drug (Sunscreen Monograph 21 CFR 352)",
        },
    ],
    "product_truth_summary": {
        "key_ingredients": ["Avobenzone", "Homosalate", "Octisalate", "Octocrylene", "Oxybenzone"],
        "hazard_signals": ["Keep out of eyes", "For external use only", "Skin cancer/skin aging alert"],
        "certifications_verified": [],
        "regulatory_status": "FDA OTC Drug under Sunscreen Monograph",
    },
    "marketing_improvement_suggestions": {
        "improved_claims_text": "Broad spectrum UVA/UVB protection. Water resistant (80 minutes). Lightweight, non-greasy feel. Trusted by dermatologists for sun protection. Designed to resist running into eyes during activity. Clinically tested SPF 50 sun protection.",
        "conversion_impact_assessment": {
            "estimated_conversion_boost_percent": 8,
            "reasoning": "Replacing absolute claims with qualified language builds consumer trust. The 'won't run into eyes' claim is a liability; the improved version maintains the benefit messaging while being defensible.",
            "key_improvements": [
                "Qualified eye-safety claim removes litigation risk",
                "Dermatologist claim softened to avoid FTC scrutiny",
                "Maintained all valid scientific claims unchanged",
            ],
        },
    },
    "report_card": {
        "ingredient_accuracy": "A",
        "regulatory_compliance": "B",
        "claim_substantiation": "B",
        "consumer_transparency": "C",
        "overall_grade": "B",
    },
}

ANALYSIS_TIDE = {
    "product_name": "Tide Original Liquid Laundry Detergent",
    "upc": "037000711209",
    "overall_verdict": "PARTIALLY_VALID",
    "confidence_score": 0.78,
    "claims_analysis": [
        {
            "original_claim": "America's #1 detergent",
            "claim_category": "Comparative Claim",
            "verdict": "NEEDS_SUBSTANTIATION",
            "severity": "MEDIUM",
            "reasoning": "Comparative superiority claims require current, reliable market share data. If based on sales data, must be clearly disclosed.",
            "regulatory_references": ["FTC Comparative Advertising Policy Statement"],
            "suggested_improvement": "America's #1 selling laundry detergent (based on sales data)",
            "evidence_from_enrichment": "No market share data in enrichment",
        },
        {
            "original_claim": "10x cleaning power",
            "claim_category": "Efficacy Claim",
            "verdict": "MISLEADING",
            "severity": "HIGH",
            "reasoning": "Vague multiplier claim without stating what it is compared against. 10x more than what? FTC requires comparative claims to identify the comparison basis.",
            "regulatory_references": ["FTC Act Section 5", "FTC Comparative Advertising"],
            "suggested_improvement": "10x the cleaning ingredients vs. the leading value detergent (by weight)",
            "evidence_from_enrichment": "Contains surfactants and enzymes (protease, amylase)",
        },
        {
            "original_claim": "Removes 99% of everyday stains",
            "claim_category": "Efficacy Claim",
            "verdict": "NEEDS_SUBSTANTIATION",
            "severity": "MEDIUM",
            "reasoning": "Specific percentage claim requires testing data. Must define 'everyday stains' and testing methodology.",
            "regulatory_references": ["FTC Advertising Substantiation Doctrine"],
            "suggested_improvement": "Tackles tough everyday stains with enzyme-powered cleaning",
            "evidence_from_enrichment": "Contains protease and amylase enzymes for stain removal",
        },
        {
            "original_claim": "Safe for all washing machines",
            "claim_category": "Safety Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Liquid detergent formulations are generally compatible with all standard washing machine types (top-load, front-load, HE).",
            "regulatory_references": [],
            "suggested_improvement": "Safe for all washing machines",
            "evidence_from_enrichment": "Standard liquid detergent formulation",
        },
        {
            "original_claim": "Contains no phosphates",
            "claim_category": "Ingredient Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Phosphates are not listed in the ingredients. US regulations have effectively banned phosphates in household laundry detergents since the 1990s.",
            "regulatory_references": ["State phosphate bans", "EPA Clean Water Act"],
            "suggested_improvement": "Contains no phosphates",
            "evidence_from_enrichment": "No phosphate compounds in ingredient list",
        },
        {
            "original_claim": "Brightens and whitens",
            "claim_category": "Efficacy Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Ingredient list contains optical brighteners (Disodium Diaminostilbene Disulfonate) and blue colorant which create whitening/brightening effect.",
            "regulatory_references": [],
            "suggested_improvement": "Brightens and whitens with optical brightener technology",
            "evidence_from_enrichment": "Contains Disodium Diaminostilbene Disulfonate, Liquitint Blue",
        },
    ],
    "product_truth_summary": {
        "key_ingredients": ["Linear Alkylbenzene Sulfonate", "Protease", "Amylase", "Alcohol Ethoxylate", "Optical Brighteners"],
        "hazard_signals": ["Warning - Causes serious eye irritation", "Causes skin irritation", "Keep out of reach of children"],
        "certifications_verified": [],
        "regulatory_status": "Consumer product, GHS classified (Eye/Skin irritation)",
    },
    "marketing_improvement_suggestions": {
        "improved_claims_text": "America's #1 selling laundry detergent (based on sales data). 10x the cleaning ingredients vs. the leading value detergent (by weight). Tackles tough everyday stains with enzyme-powered cleaning. Safe for all washing machines. Contains no phosphates. Brightens and whitens with optical brightener technology.",
        "conversion_impact_assessment": {
            "estimated_conversion_boost_percent": 12,
            "reasoning": "Clarifying the '10x' comparison and substantiating the #1 claim with specific data builds credibility. Enzyme-powered messaging adds a science-backed angle that resonates with informed consumers.",
            "key_improvements": [
                "Specified comparison basis for 10x claim",
                "Added sales data qualification for #1 claim",
                "Replaced vague stain percentage with ingredient-backed messaging",
            ],
        },
    },
    "report_card": {
        "ingredient_accuracy": "A",
        "regulatory_compliance": "C",
        "claim_substantiation": "C",
        "consumer_transparency": "B",
        "overall_grade": "C",
    },
}

ANALYSIS_AVEENO = {
    "product_name": "Aveeno Daily Moisturizing Lotion",
    "upc": "381370044307",
    "overall_verdict": "VALID",
    "confidence_score": 0.92,
    "claims_analysis": [
        {
            "original_claim": "Clinically proven to moisturize for 24 hours",
            "claim_category": "Efficacy Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "As an OTC skin protectant drug, clinical testing is required. The 24-hour moisturization claim is substantiated by colloidal oatmeal's well-documented skin protectant properties.",
            "regulatory_references": ["FDA Skin Protectant Monograph"],
            "suggested_improvement": "Clinically proven to moisturize for 24 hours",
            "evidence_from_enrichment": "Active: Colloidal Oatmeal 1%, FDA OTC Drug",
        },
        {
            "original_claim": "Fragrance-free",
            "claim_category": "Ingredient Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "No fragrance listed in ingredients. 'Fragrance-free' is a verifiable ingredient claim.",
            "regulatory_references": ["FDA cosmetic labeling requirements"],
            "suggested_improvement": "Fragrance-free",
            "evidence_from_enrichment": "No fragrance in ingredient list",
        },
        {
            "original_claim": "Hypoallergenic",
            "claim_category": "Safety Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "While FDA does not formally define 'hypoallergenic,' the product's fragrance-free, simplified ingredient list supports this claim.",
            "regulatory_references": ["FDA cosmetic labeling — hypoallergenic not formally defined"],
            "suggested_improvement": "Hypoallergenic",
            "evidence_from_enrichment": "Fragrance-free, simplified ingredient list",
        },
        {
            "original_claim": "Made with natural colloidal oatmeal",
            "claim_category": "Natural/Organic Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Colloidal oatmeal (Avena Sativa) is naturally derived and is the active ingredient in this formulation at 1%.",
            "regulatory_references": ["FDA OTC Skin Protectant Active Ingredient"],
            "suggested_improvement": "Made with natural colloidal oatmeal",
            "evidence_from_enrichment": "Avena Sativa (Oat) Kernel Flour confirmed in ingredients",
        },
        {
            "original_claim": "Dermatologist recommended",
            "claim_category": "Certification Claim",
            "verdict": "NEEDS_SUBSTANTIATION",
            "severity": "MEDIUM",
            "reasoning": "Like most 'dermatologist recommended' claims, this requires survey substantiation showing meaningful recommendation rates.",
            "regulatory_references": ["FTC Endorsement Guides 16 CFR 255"],
            "suggested_improvement": "Trusted by dermatologists",
            "evidence_from_enrichment": "No dermatologist survey data in enrichment",
        },
        {
            "original_claim": "Non-comedogenic",
            "claim_category": "Safety Claim",
            "verdict": "VALID",
            "severity": "LOW",
            "reasoning": "Product formulation avoids known comedogenic ingredients. Contains dimethicone (non-comedogenic) as emollient.",
            "regulatory_references": [],
            "suggested_improvement": "Non-comedogenic",
            "evidence_from_enrichment": "Dimethicone-based, no highly comedogenic oils",
        },
    ],
    "product_truth_summary": {
        "key_ingredients": ["Colloidal Oatmeal", "Glycerin", "Petrolatum", "Dimethicone"],
        "hazard_signals": ["For external use only"],
        "certifications_verified": ["National Eczema Association Seal of Acceptance"],
        "regulatory_status": "FDA OTC Drug (Skin Protectant)",
    },
    "marketing_improvement_suggestions": {
        "improved_claims_text": "Clinically proven to moisturize for 24 hours. Fragrance-free. Hypoallergenic. Made with natural colloidal oatmeal. Trusted by dermatologists. Non-comedogenic. Accepted by the National Eczema Association.",
        "conversion_impact_assessment": {
            "estimated_conversion_boost_percent": 5,
            "reasoning": "Claims are already well-substantiated. Adding the NEA certification mention would boost credibility. Minor improvement to dermatologist claim reduces regulatory risk.",
            "key_improvements": [
                "Added NEA certification mention for credibility",
                "Softened dermatologist claim",
                "All other claims maintained as-is",
            ],
        },
    },
    "report_card": {
        "ingredient_accuracy": "A",
        "regulatory_compliance": "A",
        "claim_substantiation": "A",
        "consumer_transparency": "A",
        "overall_grade": "A",
    },
}

LLM_ANALYSIS_STUBS = {
    "041100001214": ANALYSIS_COPPERTONE,
    "037000711209": ANALYSIS_TIDE,
    "381370044307": ANALYSIS_AVEENO,
}


def get_stub_enrichment(upc):
    """Return stubbed enrichment response for a UPC."""
    if upc in ENRICHMENT_STUBS:
        return {"success": True, "data": ENRICHMENT_STUBS[upc]}
    return {"success": True, "data": {
        "upc": upc,
        "canonicalBrand": "Unknown",
        "canonicalDescription": "Unknown Product",
        "ingredients": ["Not available"],
        "regulatoryStatus": "Unknown",
    }}


def get_stub_llm_response(upc):
    """Return stubbed LLM analysis for a UPC."""
    analysis = LLM_ANALYSIS_STUBS.get(upc)
    if analysis:
        return {"success": True, "text": json.dumps(analysis, indent=2)}
    # Generate a generic valid response for unknown products
    return {"success": True, "text": json.dumps({
        "product_name": "Unknown Product",
        "upc": upc,
        "overall_verdict": "PARTIALLY_VALID",
        "confidence_score": 0.5,
        "claims_analysis": [],
        "product_truth_summary": {"key_ingredients": [], "hazard_signals": [], "certifications_verified": [], "regulatory_status": "Unknown"},
        "marketing_improvement_suggestions": {"improved_claims_text": "", "conversion_impact_assessment": {"estimated_conversion_boost_percent": 0, "reasoning": "No data", "key_improvements": []}},
        "report_card": {"ingredient_accuracy": "C", "regulatory_compliance": "C", "claim_substantiation": "C", "consumer_transparency": "C", "overall_grade": "C"},
    }, indent=2)}


def get_stub_claude_api_response(upc):
    """Return stubbed Anthropic Claude API raw response."""
    analysis = LLM_ANALYSIS_STUBS.get(upc, {})
    return _build_claude_response(analysis)


def get_stub_gemini_api_response(upc):
    """Return stubbed Gemini API raw response."""
    analysis = LLM_ANALYSIS_STUBS.get(upc, {})
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(analysis, indent=2)}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 800},
    }
