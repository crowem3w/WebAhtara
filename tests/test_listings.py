import pytest
from fastapi.testclient import TestClient

from api import routes
from api.main import app
from listings.models import Category, Claim, Listing, Source, TrustTier
from listings.services import upsert_listing

client = TestClient(app)
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def osm():
    return Source.objects.create(
        slug="osm", name="OpenStreetMap", kind="osm", license="ODbL 1.0",
        attribution="© OpenStreetMap contributors", default_tier=TrustTier.SOURCE_LISTED, auto_publish=True,
    )


def make(osm, ext="node/1", **over):
    data = dict(name="Demo Resort", category=Category.ACCOMMODATION, city="Moalboal", province="Cebu",
                latitude=9.95, longitude=123.39, website="https://example.com", phone="+63 900 000 0000")
    data.update(over)
    return upsert_listing(osm, ext, data)[0]


def test_reimport_does_not_duplicate(osm):
    a, created = upsert_listing(osm, "node/1", dict(name="A"))
    b, created2 = upsert_listing(osm, "node/1", dict(name="A renamed"))
    assert created and not created2 and a.pk == b.pk and Listing.objects.count() == 1


def test_import_never_overwrites_owner_verified(osm):
    l = make(osm)
    Listing.objects.filter(pk=l.pk).update(trust_tier=TrustTier.OWNER_VERIFIED, name="Owner Name")
    upsert_listing(osm, "node/1", dict(name="Crowd Name"))
    assert Listing.objects.get(pk=l.pk).name == "Owner Name"


def test_public_api_hides_drafts_and_low_tiers(osm):
    make(osm, "node/1")
    make(osm, "node/2", name="Draft Place")
    Listing.objects.filter(name="Draft Place").update(status=Listing.Status.DRAFT)
    names = [i["name"] for i in client.get("/v1/listings").json()["items"]]
    assert names == ["Demo Resort"]


def test_contact_details_only_for_owner_verified(osm):
    l = make(osm)
    assert client.get(f"/v1/listings/{l.slug}").json()["phone"] is None
    Listing.objects.filter(pk=l.pk).update(trust_tier=TrustTier.OWNER_VERIFIED)
    assert client.get(f"/v1/listings/{l.slug}").json()["phone"] == "+63 900 000 0000"


def test_attribution_is_returned(osm):
    l = make(osm)
    att = client.get(f"/v1/listings/{l.slug}").json()["attributions"]
    assert att[0]["license"] == "ODbL 1.0"


def test_claim_verified_via_meta_tag(osm, monkeypatch):
    l = make(osm)
    r = client.post(f"/v1/listings/{l.slug}/claims", json={"claimant_email": "owner@example.com"})
    assert r.status_code == 201
    claim_id, token = r.json()["claim_id"], r.json()["token"]

    async def fake_fetch(url):
        return f'<html><head><meta name="ahtara-site-verification" content="{token}"></head></html>'

    monkeypatch.setattr(routes, "fetch_public_html", fake_fetch)
    v = client.post(f"/v1/claims/{claim_id}/verify", json={"token": token}).json()
    assert v["verified"] is True
    l.refresh_from_db()
    assert l.trust_tier == TrustTier.OWNER_VERIFIED and l.owner_email == "owner@example.com"
    assert Claim.objects.get(pk=claim_id).status == "verified"


def test_claim_rejects_wrong_token(osm):
    l = make(osm)
    cid = client.post(f"/v1/listings/{l.slug}/claims", json={"claimant_email": "o@example.com"}).json()["claim_id"]
    assert client.post(f"/v1/claims/{cid}/verify", json={"token": "nope"}).status_code == 403


def test_safe_fetch_blocks_private_hosts():
    import asyncio

    from api.safe_fetch import UnsafeURL, fetch_public_html

    with pytest.raises(UnsafeURL):
        asyncio.run(fetch_public_html("http://127.0.0.1/"))
