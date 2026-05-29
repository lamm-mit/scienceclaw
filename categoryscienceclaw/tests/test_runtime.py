import json
from dataclasses import replace

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.cli import _init, _run
from categoryscienceclaw.kernel.models import AgentProfile, Artifact, MorphismSignature
from categoryscienceclaw.proofs.certificates import build_execution_certificate
from categoryscienceclaw.proofs.hashing import canonical_hash
from categoryscienceclaw.runtime.claims import ClaimRegistry
from categoryscienceclaw.runtime.store import RunStore


def write_agents(path):
    data = {
        "agents": [
            {"name": "LiteratureAgent", "morphisms": ["literature_search"]},
            {"name": "ComputationAgent", "morphisms": ["computational_analysis"]},
            {"name": "SynthesisAgent", "morphisms": ["synthesize_claim"]},
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_decentralized_run_produces_claim_and_audits(tmp_path):
    run_dir = tmp_path / "run"
    agents_path = tmp_path / "agents.json"
    write_agents(agents_path)

    assert _init(str(run_dir), "Does mechanism X hold?", str(agents_path)) == 0
    assert _run(str(run_dir), str(agents_path), cycles=5, use_scienceclaw=False) == 0

    store = RunStore(run_dir)
    artifacts = store.list_artifacts()
    assert [artifact.type for artifact in artifacts].count("Claim") == 1
    assert store.open_needs() == []

    claim = next(artifact for artifact in artifacts if artifact.type == "Claim")
    assert len(claim.parent_ids) == 2

    report = audit_run(store)
    assert report.ok, report.errors
    assert report.counts["certificates"] == 3


def test_claim_registry_allows_only_one_agent(tmp_path):
    registry = ClaimRegistry(tmp_path / "claims.jsonl")

    assert registry.try_claim("need:one:0", "AgentA")
    assert registry.try_claim("need:one:0", "AgentB") is None
    assert registry.active_claims()["need:one:0"] == "AgentA"


def test_certificate_detects_bad_input_type():
    morphism = MorphismSignature(
        name="bad",
        input_types=("ResearchQuestion",),
        output_type="LiteratureEvidence",
    )
    parent = Artifact.create(
        artifact_type="ComputationalAnalysis",
        payload={"x": 1},
        producer_agent="A",
    )
    output = Artifact.create(
        artifact_type="LiteratureEvidence",
        payload={"y": 2},
        producer_agent="A",
        morphism="bad",
        parent_ids=[parent.id],
    )

    cert = build_execution_certificate(
        morphism=morphism,
        inputs=[parent],
        output=output,
        claim_id="claim-1",
    )

    assert not cert.ok
    assert any("type mismatch" in error for error in cert.errors)


def test_audit_detects_content_hash_mismatch(tmp_path):
    run_dir = tmp_path / "run"
    agents_path = tmp_path / "agents.json"
    write_agents(agents_path)
    _init(str(run_dir), "hash check", str(agents_path))

    store = RunStore(run_dir)
    artifact = store.list_artifacts()[0]
    corrupted = replace(artifact, payload={"topic": "changed"}, content_hash=canonical_hash({"topic": "hash check"}))
    store.artifacts_path.write_text(json.dumps(corrupted.to_dict()) + "\n", encoding="utf-8")

    report = audit_run(store)
    assert not report.ok
    assert any("content hash mismatch" in error for error in report.errors)
