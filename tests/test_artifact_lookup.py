import json
import sys
from unittest.mock import Mock

from artifacts.artifact import Artifact, ArtifactStore


def test_reader_finds_artifact_saved_after_initial_lookup(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(ArtifactStore, "_sync_to_infinite", Mock())
    monkeypatch.setitem(sys.modules, "paraxiom_trust", Mock())
    reader = ArtifactStore("physics")
    writer = ArtifactStore("physics")
    first = Artifact.create("analysis_result", "physics", "fit", {"unit": "µm"})
    second = Artifact.create("analysis_result", "physics", "fit", {"unit": "nm"})

    writer.save(first)
    assert reader.get(first.artifact_id) == first
    assert reader.get(second.artifact_id) is None
    writer.save(second)
    assert reader.get(second.artifact_id) == second
    assert reader.get(first.artifact_id) == first


def test_lookup_retries_incomplete_final_record(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reader = ArtifactStore("physics")
    artifact = Artifact.create("analysis_result", "physics", "fit", {"unit": "nm"})
    record = json.dumps(artifact.to_dict())
    with reader.store_path.open("w", encoding="utf-8") as writer:
        writer.write(record[:20])
        writer.flush()
        assert reader.get(artifact.artifact_id) is None
        writer.write(record[20:] + "\n")
    assert reader.get(artifact.artifact_id) == artifact
