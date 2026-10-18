"""Write-side logic shared by the admin, management commands, importers and the API."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import Claim, Listing, ListingSource, Source, TrustTier

# Fields an importer may set / refresh on a listing.
IMPORTABLE_FIELDS = (
    "name", "category", "description", "address", "city", "province", "region",
    "latitude", "longitude", "website", "phone", "email",
)


def make_unique_slug(name: str, hint: str = "") -> str:
    base = slugify(f"{name} {hint}".strip())[:140] or "listing"
    slug, n = base, 2
    while Listing.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


@transaction.atomic
def upsert_listing(source: Source, external_id: str, data: dict, source_url: str = "", raw: dict | None = None) -> tuple[Listing, bool]:
    """
    Create or refresh a listing coming from `source`. Importers (OSM, DOT lists, LGU CSVs...) call this.

    Returns (listing, created). Rules:
      * provenance is recorded in ListingSource, keyed by (source, external_id), so re-imports never duplicate;
      * owner-verified listings are never overwritten by an import (the owner is the authority);
      * a re-import never lowers the trust tier.
    """
    unknown = set(data) - set(IMPORTABLE_FIELDS)
    if unknown:
        raise ValueError(f"Unknown listing fields: {sorted(unknown)}")

    link = ListingSource.objects.select_related("listing").filter(source=source, external_id=external_id).first()
    if link:
        listing = link.listing
        if listing.trust_tier < TrustTier.OWNER_VERIFIED:
            for field, value in data.items():
                setattr(listing, field, value)
            listing.trust_tier = max(listing.trust_tier, source.default_tier)
            listing.save()
        link.source_url = source_url or link.source_url
        link.raw = raw or link.raw
        link.save()  # bumps fetched_at
        return listing, False

    listing = Listing.objects.create(
        slug=make_unique_slug(data.get("name", "listing"), data.get("city", "")),
        trust_tier=source.default_tier,
        status=Listing.Status.PUBLISHED if source.auto_publish else Listing.Status.DRAFT,
        **data,
    )
    ListingSource.objects.create(listing=listing, source=source, external_id=external_id, source_url=source_url, raw=raw or {})
    return listing, True


@transaction.atomic
def approve_claim(claim: Claim, reviewer=None) -> None:
    """Mark a claim verified and promote its listing to OWNER_VERIFIED."""
    now = timezone.now()
    claim.status = Claim.Status.VERIFIED
    claim.verified_at = now
    if reviewer is not None:
        claim.reviewed_by = reviewer
    claim.save()

    listing = claim.listing
    listing.trust_tier = TrustTier.OWNER_VERIFIED
    listing.owner_email = claim.claimant_email
    listing.last_verified_at = now
    listing.save()
