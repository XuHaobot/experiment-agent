"""
Test Suite for ResearchOS V2.5 Phase 15 — Local AI Gateway & Privacy Boundary
Covers:
1. Ollama Provider Health / Mock fallback
2. PUBLIC -> ALLOW
3. SENSITIVE -> ASK
4. RESTRICTED -> DENY
5. DENY -> LLM Provider NEVER called (Hard block verification)
6. ASK -> No call before approval
7. ASK -> Approval -> LLM call
8. LOCAL_ONLY -> Cloud Provider prohibited
9. Research Agent -> Context -> Privacy Gateway -> LLM Gateway -> Provider full flow
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.llm.base import RoutingPolicy, ProviderType
from backend.llm.gateway import llm_gateway
from backend.llm.providers.mock import MockProvider
from backend.llm.context import ContextPlanner, ResearchContext
from backend.security.classification import DataClassification, PrivacyDecision
from backend.security.privacy_gateway import privacy_gateway, PrivacyViolationError
from backend.security.audit import get_privacy_audit_logs

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_gateway_fixture():
    # Setup deterministic mock provider as active for testing
    mock_prov = MockProvider(
        name="mock_test",
        default_model="mock-v25-test",
        custom_responses={
            "hypothesis": "Hypothesis analysis: Adaptive update rate preserves manifold geometry.",
            "literature": "Synthesized literature summary from OpenAlex and arXiv.",
            "general": "Scientific inference complete.",
        },
        is_local=True,
    )
    llm_gateway.register_provider(mock_prov)
    llm_gateway.set_active_provider("mock_test")
    llm_gateway.set_routing_policy(RoutingPolicy.LOCAL_PREFERRED)
    yield
    # Reset routing policy to default
    llm_gateway.set_routing_policy(RoutingPolicy.LOCAL_PREFERRED)


# =============================================================================
# TEST 1: Ollama Provider Health & Fallback
# =============================================================================
def test_01_ollama_provider_health_and_list():
    resp = client.get("/api/llm/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert any(p["name"] == "ollama" for p in data["providers"])
    
    # Ollama health check endpoint
    h_resp = client.get("/api/llm/providers/ollama/health")
    assert h_resp.status_code == 200
    health_data = h_resp.json()
    assert health_data["provider"] == "ollama"
    assert health_data["is_local"] is True
    # If Ollama daemon is offline in test env, it returns "disconnected" without crashing
    assert health_data["status"] in ("connected", "disconnected", "error")


# =============================================================================
# TEST 2: PUBLIC -> ALLOW
# =============================================================================
def test_02_public_classification_allows_transmission():
    public_text = "Topological Invariants in Dynamic Graph Convolutional Networks (DOI: 10.1000/182, Authors: Lin & Wang, Year: 2026)"
    check_resp = client.post("/api/privacy/check", json={"text": public_text, "is_local_llm": True})
    assert check_resp.status_code == 200
    res = check_resp.json()
    assert res["decision"] == "ALLOW"
    assert res["allowed"] is True
    assert res["classification"] == "PUBLIC"


# =============================================================================
# TEST 3: SENSITIVE -> ASK
# =============================================================================
def test_03_sensitive_classification_requires_approval():
    sensitive_context = [
        {
            "source_type": "hypothesis",
            "source_id": "hyp_001",
            "content": "Unpublished hypothesis: Adaptive edge rates prevent manifold collapse",
            "classification": "SENSITIVE",
        }
    ]
    check_resp = client.post("/api/privacy/check", json={"items": sensitive_context, "is_local_llm": True})
    assert check_resp.status_code == 200
    res = check_resp.json()
    assert res["decision"] == "ASK"
    assert res["allowed"] is False
    assert res["ticket_id"] is not None
    assert "ticket_id" in res


# =============================================================================
# TEST 4: RESTRICTED -> DENY
# =============================================================================
def test_04_restricted_classification_triggers_hard_block():
    restricted_data = "patient_id,mrn,heart_rate\nP001,MRN_9921,78\nP002,MRN_9922,82\nAPI_KEY=sk-abcdef1234567890123456"
    check_resp = client.post("/api/privacy/check", json={"text": restricted_data, "is_local_llm": True})
    assert check_resp.status_code == 200
    res = check_resp.json()
    assert res["decision"] == "DENY"
    assert res["allowed"] is False
    assert res["classification"] == "RESTRICTED"


# =============================================================================
# TEST 5: DENY -> LLM Provider NEVER called (Hard Block)
# =============================================================================
def test_05_deny_ensures_llm_provider_is_never_called():
    mock_prov: MockProvider = llm_gateway.get_provider("mock_test")
    initial_calls = len(mock_prov.call_history)

    restricted_prompt = "Classified Patient medical records: subject_name=Alice, ssn=000-11-2222, api_key=sk-1234567890abcdef"
    chat_resp = client.post("/api/llm/chat", json={"prompt": restricted_prompt})
    
    # 403 Forbidden with PRIVACY_DENIED
    assert chat_resp.status_code == 403
    err_body = chat_resp.json()
    assert err_body["detail"]["error"] == "PRIVACY_DENIED"

    # Verify provider was NEVER touched
    assert len(mock_prov.call_history) == initial_calls


# =============================================================================
# TEST 6: ASK -> No call before approval
# =============================================================================
def test_06_ask_blocks_call_before_user_approval():
    mock_prov: MockProvider = llm_gateway.get_provider("mock_test")
    initial_calls = len(mock_prov.call_history)

    sensitive_text = "Unpublished draft hypothesis hyp_topological_noise: parameter k=20"
    chat_resp = client.post("/api/llm/chat", json={"prompt": sensitive_text})
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["finish_reason"] == "privacy_approval_required"
    assert "PRIVACY_GATE_REQUIRED" in data["content"]
    assert "ticket_id" in data["raw_response"]

    # Provider was NOT invoked with unapproved sensitive payload
    assert len(mock_prov.call_history) == initial_calls


# =============================================================================
# TEST 7: ASK -> User Approval -> LLM call executes
# =============================================================================
def test_07_ask_executes_after_user_approval():
    sensitive_text = "Unpublished draft hypothesis hyp_topological_noise: parameter k=20"
    
    # Step 1: Trigger gate & get ticket
    check_resp = client.post("/api/privacy/check", json={"text": sensitive_text, "is_local_llm": True})
    ticket_id = check_resp.json()["ticket_id"]
    assert ticket_id is not None

    # Step 2: Authorize ticket via API
    auth_resp = client.post("/api/privacy/authorize", json={"ticket_id": ticket_id, "action": "allow_once"})
    assert auth_resp.status_code == 200
    assert auth_resp.json()["ok"] is True

    # Step 3: Call with approved ticket
    chat_resp = client.post("/api/llm/chat", json={
        "prompt": sensitive_text,
        "approved_ticket_id": ticket_id,
    })
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["finish_reason"] == "stop"
    assert "Hypothesis analysis" in data["content"] or "MOCK RESPONSE" in data["content"]


# =============================================================================
# TEST 8: LOCAL_ONLY -> Cloud Provider prohibited
# =============================================================================
def test_08_local_only_policy_blocks_cloud_provider():
    # Register a cloud provider
    cloud_mock = MockProvider(name="cloud_mock", default_model="cloud-model", is_local=False)
    llm_gateway.register_provider(cloud_mock)

    # Set policy to LOCAL_ONLY
    llm_gateway.set_routing_policy(RoutingPolicy.LOCAL_ONLY)

    # Attempt to transmit through cloud provider
    with pytest.raises(PrivacyViolationError) as exc_info:
        llm_gateway.safe_chat(
            messages="General scientific inquiry",
            provider_name="cloud_mock",
        )
    assert "LOCAL_ONLY" in str(exc_info.value)


# =============================================================================
# TEST 9: Research Agent -> Context -> Privacy Gateway -> LLM Gateway -> Provider Full Flow
# =============================================================================
def test_09_full_agent_context_privacy_pipeline():
    project_id = "proj_test_v25_phase15"
    
    # Build a structured research context
    ctx = ResearchContext(project_id=project_id, query_intent="synthesize_evidence")
    ctx.add_item(
        source_type="paper",
        source_id="paper_101",
        content="Lin et al. (2026) studied topological manifolds under 15% noise.",
        classification=DataClassification.PUBLIC,
        reason="Open scientific paper",
    )
    ctx.add_item(
        source_type="dataset_schema",
        source_id="ds_noise_01",
        content="Columns: [sample_id, group, stability_metric], Rows: 100",
        classification=DataClassification.PUBLIC,
        reason="Dataset schema definition",
    )

    # Execute through LLMGateway
    res = llm_gateway.safe_chat(
        messages="Please summarize the research evidence based on the attached context.",
        project_id=project_id,
        context=ctx,
        provider_name="mock_test",
    )
    assert res.finish_reason == "stop"
    assert len(res.content) > 0

    # Verify audit trail was recorded
    audit_logs = get_privacy_audit_logs(limit=10)
    assert len(audit_logs) >= 1
    recent = audit_logs[0]
    assert recent["decision"] in ("ALLOW", "ASK", "DENY")
    assert "highest_classification" in recent
