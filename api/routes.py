from __future__ import annotations

import re

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Q
from fastapi import APIRouter, HTTPException, Query

from listings.models import Category, Claim, Listing, Report
from listings.services import approve_claim

from .safe_fetch import fetch_public_html
from .schemas import ClaimIn, ClaimOut, ListingOut, ListingPage, ReportIn, ReportOut, VerifyIn, VerifyOut

router = APIRouter()


def public_listings():
    """The only queryset the public API reads from: published, and trusted enough."""
    return (
        Listing.objects.filter(status=Listing.Status.PUBLISHED, trust_tier__gte=settings.PUBLIC_MIN_TIER)
        .prefetch_related("sources__source")
    )


@router.get("/listings", response_model=ListingPage)
async def list_listings(
    q: str | None = Query(None, description="Matches name or city"),
    category: Category | None = None,
    province: str | None = None,
    region: str | None = None,
    min_tier: int = Query(0, ge=0, le=3, description="Only listings at or above this trust tier"),
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    qs = public_listings()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q))
    if category:
        qs = qs.filter(category=category.value)
    if province:
        qs = qs.filter(province__iexact=province)
    if region:
        qs = qs.filter(region__iexact=region)
    if min_tier:
        qs = qs.filter(trust_tier__gte=min_tier)
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = (float(x) for x in bbox.split(","))
        except ValueError:
            raise HTTPException(422, "bbox must be minLon,minLat,maxLon,maxLat")
        qs = qs.filter(longitude__gte=min_lon, longitude__lte=max_lon, latitude__gte=min_lat, latitude__lte=max_lat)

    qs = qs.order_by("-trust_tier", "name")
    total = await qs.acount()
    items = [ListingOut.from_model(l) async for l in qs[offset : offset + limit]]
    return ListingPage(total=total, limit=limit, offset=offset, items=items)


async def _get_public(slug: str) -> Listing:
    try:
        return await public_listings().aget(slug=slug)
    except Listing.DoesNotExist:
        raise HTTPException(404, "Listing not found")


@router.get("/listings/{slug}", response_model=ListingOut)
async def get_listing(slug: str):
    return ListingOut.from_model(await _get_public(slug))


@router.post("/listings/{slug}/reports", response_model=ReportOut, status_code=201)
async def report_listing(slug: str, body: ReportIn):
    listing = await _get_public(slug)
    report = await Report.objects.acreate(listing=listing, message=body.message, contact_email=body.contact_email or "")
    return ReportOut(id=report.pk, status=report.status)


@router.post("/listings/{slug}/claims", response_model=ClaimOut, status_code=201)
async def start_claim(slug: str, body: ClaimIn):
    listing = await _get_public(slug)
    if listing.trust_tier == 3:
        raise HTTPException(409, "This listing is already owner-verified. Contact support to dispute it.")
    if body.method == "meta_tag" and not listing.website:
        raise HTTPException(422, "This listing has no website to verify; use method=manual.")
    claim = await Claim.objects.acreate(listing=listing, claimant_email=body.claimant_email, method=body.method)
    if claim.method == Claim.Method.META_TAG:
        instructions = (
            f'Add <meta name="{settings.VERIFICATION_META_NAME}" content="{claim.token}"> to the <head> of {listing.website}, '
            f"then call POST /v1/claims/{claim.pk}/verify with this token."
        )
    else:
        instructions = "A reviewer will contact you at the claimant email to check your registration documents."
    return ClaimOut(claim_id=claim.pk, method=claim.method, status=claim.status, token=claim.token, instructions=instructions)


@router.post("/claims/{claim_id}/verify", response_model=VerifyOut)
async def verify_claim(claim_id: int, body: VerifyIn):
    try:
        claim = await Claim.objects.select_related("listing").aget(pk=claim_id)
    except Claim.DoesNotExist:
        raise HTTPException(404, "Claim not found")
    if body.token != claim.token:
        raise HTTPException(403, "Wrong token")
    if claim.status != Claim.Status.PENDING:
        return VerifyOut(verified=claim.status == Claim.Status.VERIFIED, detail=f"Claim is {claim.status}")
    if claim.method != Claim.Method.META_TAG:
        return VerifyOut(verified=False, detail="This claim needs manual review")

    try:
        html = await fetch_public_html(claim.listing.website)
    except Exception as exc:  # UnsafeURL, network errors, bad status
        return VerifyOut(verified=False, detail=f"Could not read the website: {type(exc).__name__}")

    name = re.escape(settings.VERIFICATION_META_NAME)
    pattern = rf'<meta[^>]+name=["\']{name}["\'][^>]+content=["\']{re.escape(claim.token)}["\']'
    pattern_rev = rf'<meta[^>]+content=["\']{re.escape(claim.token)}["\'][^>]+name=["\']{name}["\']'
    if re.search(pattern, html, re.I) or re.search(pattern_rev, html, re.I):
        await sync_to_async(approve_claim)(claim)
        return VerifyOut(verified=True, detail="Ownership verified")
    return VerifyOut(verified=False, detail="Meta tag not found on the home page yet")


@router.get("/health")
async def health():
    return {"status": "ok"}
