import os
import json
from typing import Any, Dict, Literal, Optional, List

from openai import OpenAI


LLMProvider = Literal["mock", "xai"]


class LLMService:
    """
    LLM facade used by all agents.

    - Default is **mock** so you can run everything 100% free.
    - To use a real LLM (Grok via xAI), set `LLM_PROVIDER=xai` and `XAI_API_KEY`.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        # Decide which backend to use
        self.provider: LLMProvider = provider or os.getenv("LLM_PROVIDER", "mock")  # type: ignore[assignment]
        if self.provider not in ("mock", "xai"):
            self.provider = "mock"

        self.model = os.getenv("LLM_MODEL_NAME", "grok-beta")
        self.client: Optional[OpenAI] = None

        # Optional real LLM backend (Grok, OpenAI‑compatible)
        if self.provider == "xai":
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "XAI_API_KEY is not set. Either set LLM_PROVIDER=mock to run "
                    "completely free, or configure XAI_API_KEY in your environment."
                )

            self.client = OpenAI(
                api_key=api_key,
                base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            )

    # ---------------------------------------------------------------------
    # Public methods used by orchestrator
    # ---------------------------------------------------------------------

    async def classify_document(self, text: str, filename: str) -> Dict[str, Any]:
        """Classify document type using LLM or mock heuristics."""

        if self.provider == "mock":
            return self._mock_classify(text, filename)

        assert self.client is not None

        prompt = f"""Classify this document into ONE of these types:
- bill (hospital bill/invoice)
- discharge_summary (discharge summary/report)
- id_card (insurance ID card)
- pharmacy_bill (pharmacy receipt/bill)
- claim_form (insurance claim form)
- other (anything else)

Document filename: {filename}
Document text (first 2000 chars):
{text[:2000]}

Respond ONLY with valid JSON in this exact format:
{{
    "document_type": "type_here",
    "confidence": 0.95
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        response_text = response.choices[0].message.content or ""
        return self._extract_json(response_text)

    async def extract_bill_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from hospital bill."""

        if self.provider == "mock":
            return self._mock_bill(text)

        assert self.client is not None

        prompt = f"""Extract structured information from this hospital bill.
Return ONLY valid JSON with these fields (use null for missing):

{{
    "hospital_name": "string or null",
    "patient_name": "string or null",
    "bill_number": "string or null",
    "bill_date": "YYYY-MM-DD or null",
    "total_amount": number or null,
    "items": [
        {{"description": "string", "amount": number}}
    ]
}}

Bill text:
{text[:3000]}

Respond with ONLY the JSON object, no other text."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    async def extract_discharge_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from discharge summary."""

        if self.provider == "mock":
            return self._mock_discharge(text)

        assert self.client is not None

        prompt = f"""Extract structured information from this discharge summary.
Return ONLY valid JSON with these fields (use null for missing):

{{
    "hospital_name": "string or null",
    "patient_name": "string or null",
    "admission_date": "YYYY-MM-DD or null",
    "discharge_date": "YYYY-MM-DD or null",
    "diagnosis": "string or null",
    "doctor_name": "string or null",
    "treatment_summary": "string or null"
}}

Discharge summary text:
{text[:3000]}

Respond with ONLY the JSON object, no other text."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    async def extract_id_card_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from insurance ID card."""

        if self.provider == "mock":
            return self._mock_id_card(text)

        assert self.client is not None

        prompt = f"""Extract structured information from this insurance ID card.
Return ONLY valid JSON with these fields (use null for missing):

{{
    "patient_name": "string or null",
    "policy_number": "string or null",
    "insurance_company": "string or null",
    "validity_date": "YYYY-MM-DD or null",
    "coverage_amount": number or null
}}

ID card text:
{text[:2000]}

Respond with ONLY the JSON object, no other text."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    async def extract_pharmacy_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from pharmacy bill."""

        if self.provider == "mock":
            return self._mock_pharmacy(text)

        assert self.client is not None

        prompt = f"""Extract structured information from this pharmacy bill.
Return ONLY valid JSON with these fields (use null for missing):

{{
    "pharmacy_name": "string or null",
    "patient_name": "string or null",
    "bill_number": "string or null",
    "bill_date": "YYYY-MM-DD or null",
    "total_amount": number or null,
    "medicines": [
        {{"name": "string", "quantity": number, "amount": number}}
    ]
}}

Pharmacy bill text:
{text[:3000]}

Respond with ONLY the JSON object, no other text."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    async def extract_claim_form_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from claim form."""

        if self.provider == "mock":
            return self._mock_claim_form(text)

        assert self.client is not None

        prompt = f"""Extract structured information from this insurance claim form.
Return ONLY valid JSON with these fields (use null for missing):

{{
    "patient_name": "string or null",
    "policy_number": "string or null",
    "claim_amount": number or null,
    "claim_date": "YYYY-MM-DD or null",
    "hospital_name": "string or null"
}}

Claim form text:
{text[:3000]}

Respond with ONLY the JSON object, no other text."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    async def validate_documents(self, documents: List[dict]) -> Dict[str, Any]:
        """Validate all documents for consistency."""

        if self.provider == "mock":
            return self._mock_validate(documents)

        assert self.client is not None

        doc_summary = "\n\n".join(
            [
                f"Document {i+1} ({doc['document_type']}):\n"
                f"{json.dumps(doc['extracted_data'], indent=2)}"
                for i, doc in enumerate(documents)
            ]
        )

        prompt = f"""Analyze these medical claim documents and identify:
1. Missing required documents (bill, discharge_summary, id_card are typically required)
2. Discrepancies (mismatched names, dates, amounts between documents)

Documents:
{doc_summary}

Return ONLY valid JSON:
{{
    "missing_documents": ["type1", "type2"],
    "discrepancies": [
        {{"field": "patient_name", "issue": "description", "severity": "high|medium|low"}}
    ],
    "is_valid": true or false
}}

Respond with ONLY the JSON object."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    async def make_claim_decision(self, documents: List[dict], validation: dict) -> Dict[str, Any]:
        """Make final claim approval decision."""

        if self.provider == "mock":
            return self._mock_decision(documents, validation)

        assert self.client is not None

        prompt = f"""Based on these medical claim documents and validation results, make a claim decision.

Validation Results:
{json.dumps(validation, indent=2)}

Number of documents: {len(documents)}
Document types: {[doc['document_type'] for doc in documents]}

Return ONLY valid JSON:
{{
    "status": "approved" or "rejected" or "manual_review",
    "reason": "explanation here",
    "confidence": 0.0 to 1.0
}}

Decision criteria:
- approved: All required docs present, no major discrepancies
- rejected: Critical missing docs or severe discrepancies
- manual_review: Minor issues or need human verification

Respond with ONLY the JSON object."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._extract_json(response.choices[0].message.content or "")

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Remove markdown code blocks if present
            cleaned = text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            try:
                # Try to find JSON inside a longer string
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = text[start:end]
                    return json.loads(json_str)
            except Exception:
                pass

        # Fallback – empty dict
        return {}

    # ---------------------------------------------------------------------
    # Mock implementations (free, deterministic behaviour)
    # ---------------------------------------------------------------------

    def _mock_classify(self, text: str, filename: str) -> Dict[str, Any]:
        """Very simple heuristic classifier that mimics LLM behaviour."""
        name = filename.lower()
        content = (text or "").lower()

        def has_any(keys):
            return any(k in content for k in keys) or any(k in name for k in keys)

        if has_any(["pharmacy", "medicine", "rx"]):
            doc_type = "pharmacy_bill"
        elif has_any(["discharge", "diagnosis", "admission"]):
            doc_type = "discharge_summary"
        elif has_any(["id card", "member id", "policy"]):
            doc_type = "id_card"
        elif has_any(["claim form", "claim no", "reimbursement"]):
            doc_type = "claim_form"
        elif has_any(["bill", "invoice", "amount", "total"]):
            doc_type = "bill"
        else:
            doc_type = "other"

        confidence = 0.9 if doc_type != "other" else 0.6
        return {
            "document_type": doc_type,
            "confidence": confidence,
        }

    def _mock_bill(self, text: str) -> Dict[str, Any]:
        return {
            "hospital_name": "Mock Hospital",
            "patient_name": "Mock Patient",
            "bill_number": "BILL-MOCK-001",
            "bill_date": "2024-01-01",
            "total_amount": 10000.0,
            "items": [
                {"description": "Room Charges", "amount": 4000.0},
                {"description": "Treatment", "amount": 6000.0},
            ],
        }

    def _mock_discharge(self, text: str) -> Dict[str, Any]:
        return {
            "hospital_name": "Mock Hospital",
            "patient_name": "Mock Patient",
            "admission_date": "2023-12-28",
            "discharge_date": "2024-01-01",
            "diagnosis": "Mock Diagnosis",
            "doctor_name": "Dr. Mock",
            "treatment_summary": "Patient admitted and treated in mock mode.",
        }

    def _mock_id_card(self, text: str) -> Dict[str, Any]:
        return {
            "patient_name": "Mock Patient",
            "policy_number": "POLICY-MOCK-123",
            "insurance_company": "Mock Insurance Co.",
            "validity_date": "2025-12-31",
            "coverage_amount": 500000.0,
        }

    def _mock_pharmacy(self, text: str) -> Dict[str, Any]:
        return {
            "pharmacy_name": "Mock Pharmacy",
            "patient_name": "Mock Patient",
            "bill_number": "PHARM-MOCK-789",
            "bill_date": "2024-01-02",
            "total_amount": 1500.0,
            "medicines": [
                {"name": "Paracetamol", "quantity": 10, "amount": 500.0},
                {"name": "Antibiotic", "quantity": 5, "amount": 1000.0},
            ],
        }

    def _mock_claim_form(self, text: str) -> Dict[str, Any]:
        return {
            "patient_name": "Mock Patient",
            "policy_number": "POLICY-MOCK-123",
            "claim_amount": 10000.0,
            "claim_date": "2024-01-03",
            "hospital_name": "Mock Hospital",
        }

    def _mock_validate(self, documents: List[dict]) -> Dict[str, Any]:
        present_types = {doc.get("document_type") for doc in documents}
        required = {"bill", "discharge_summary", "id_card"}
        missing = sorted(required - present_types)

        discrepancies: List[Dict[str, Any]] = []

        # Very small name consistency check
        all_names = {
            doc.get("document_type"): (doc.get("extracted_data") or {}).get("patient_name")
            for doc in documents
        }
        names = {v for v in all_names.values() if v}
        if len(names) > 1:
            discrepancies.append(
                {
                    "field": "patient_name",
                    "issue": f"Inconsistent patient_name across documents: {all_names}",
                    "severity": "medium",
                }
            )

        is_valid = not missing and not discrepancies
        return {
            "missing_documents": missing,
            "discrepancies": discrepancies,
            "is_valid": is_valid,
        }

    def _mock_decision(self, documents: List[dict], validation: dict) -> Dict[str, Any]:
        missing = validation.get("missing_documents") or []
        discrepancies = validation.get("discrepancies") or []

        if not missing and not discrepancies:
            return {
                "status": "approved",
                "reason": "All required documents present and consistent (mock decision).",
                "confidence": 0.9,
            }

        if missing and any(d.get("severity") == "high" for d in discrepancies):
            return {
                "status": "rejected",
                "reason": "Critical issues and missing documents detected (mock decision).",
                "confidence": 0.85,
            }

        return {
            "status": "manual_review",
            "reason": "Some documents missing or inconsistencies found (mock decision).",
            "confidence": 0.7,
        }


