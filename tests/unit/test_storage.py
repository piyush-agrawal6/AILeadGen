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
    client.head_object.return_value={'ContentLength':3,'ContentType':'text/csv'}
    storage=R2ArtifactStorage(client)
    storage.put("campaigns/test/runs/1/leads.csv",source,"text/csv")
    assert "ACL" not in client.upload_file.call_args.kwargs["ExtraArgs"]
    assert client.upload_file.call_args.kwargs["ExtraArgs"]["CacheControl"]=="private, no-store"
    assert storage.get("campaigns/test/runs/1/leads.csv").read()==b"csv"
    client.head_object.return_value['ContentLength']=2
    with pytest.raises(IOError,match='metadata differs'):storage.put('campaigns/test/runs/1/leads.csv',source,'text/csv')

def test_historical_and_new_pdf_keys_route_independently(monkeypatch):
    from app import storage
    from uuid import uuid4
    legacy,reports=Mock(),Mock();monkeypatch.setattr(storage,'R2ArtifactStorage',lambda *,reports=False:stores[reports]);stores={False:legacy,True:reports}
    old='prospects/fixture/reports/old.pdf';new=storage.workspace_report_key(str(uuid4()),str(uuid4()));backend=storage.RoutedR2Storage()
    backend.get(old);backend.get(new);legacy.get.assert_called_once_with(old);reports.get.assert_called_once_with(new)
    backend.delete_many([new,old]);legacy.delete_many.assert_called_once_with([old]);reports.delete_many.assert_called_once_with([new])
    with pytest.raises(ValueError):backend.put(new,'unused','text/html')
    with pytest.raises(ValueError):backend.get(new.replace('report.pdf','../report.pdf'))
