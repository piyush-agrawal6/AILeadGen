from io import BytesIO
from unittest.mock import Mock
import pytest
from app.storage import LocalArtifactStorage, R2ArtifactStorage, validate_key


@pytest.mark.parametrize("key",["../secrets","campaigns/../../secret","campaigns//run.csv","/campaigns/run.csv","campaigns/%2e%2e/secret","arbitrary/file.csv"])
def test_object_path_traversal_rejected(key):
    with pytest.raises(ValueError):validate_key(key)


def test_local_storage_round_trip(tmp_path):
    source=tmp_path/"file.csv";source.write_text("business,score\nExample,90")
    storage=LocalArtifactStorage(tmp_path/"objects")
    storage.put("campaigns/test/runs/1/leads.csv",source,"text/csv")
    with storage.get("campaigns/test/runs/1/leads.csv") as body:assert body.read()==source.read_bytes()


def test_private_r2_contract(tmp_path):
    source=tmp_path/"file.csv";source.write_text("csv")
    client=Mock();client.get_object.return_value={"Body":BytesIO(b"csv")}
    storage=R2ArtifactStorage(client)
    storage.put("campaigns/test/runs/1/leads.csv",source,"text/csv")
    assert "ACL" not in client.upload_file.call_args.kwargs["ExtraArgs"]
    assert client.upload_file.call_args.kwargs["ExtraArgs"]["CacheControl"]=="private, no-store"
    assert storage.get("campaigns/test/runs/1/leads.csv").read()==b"csv"
