from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from listings.models import Listing, TrustTier

TIER_KEYS = {
    TrustTier.UNVERIFIED: "unverified",
    TrustTier.SOURCE_LISTED: "source_listed",
    TrustTier.REGISTRY_CHECKED: "registry_checked",
    TrustTier.OWNER_VERIFIED: "owner_verified",
}


class AttributionOut(BaseModel):
    source: str
    kind: str
    attribution: str
    license: str
    url: str


class ListingOut(BaseModel):
    slug: str
    name: str
    category: str
    description: str
    address: str
    city: str
    province: str
    region: str
    latitude: float | None
    longitude: float | None
    website: str
    # Contact details are only present once the owner verified the listing.
    phone: str | None
    email: str | None
    trust_tier: str
    trust_label: str
    last_verified_at: datetime | None
    attributions: list[AttributionOut]

    @classmethod
    def from_model(cls, l: Listing) -> "ListingOut":
        owner_verified = l.trust_tier == TrustTier.OWNER_VERIFIED
        seen, attributions = set(), []
        for link in l.sources.all():
            s = link.source
            if s.pk in seen or not (s.attribution or s.license):
                continue
            seen.add(s.pk)
            attributions.append(AttributionOut(source=s.name, kind=s.kind, attribution=s.attribution, license=s.license, url=s.url))
        return cls(
            slug=l.slug, name=l.name, category=l.category, description=l.description, address=l.address,
            city=l.city, province=l.province, region=l.region, latitude=l.latitude, longitude=l.longitude,
            website=l.website,
            phone=(l.phone or None) if owner_verified else None,
            email=(l.email or None) if owner_verified else None,
            trust_tier=TIER_KEYS[TrustTier(l.trust_tier)],
            trust_label=TrustTier(l.trust_tier).label,
            last_verified_at=l.last_verified_at,
            attributions=attributions,
        )


class ListingPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ListingOut]


class ReportIn(BaseModel):
    message: str = Field(min_length=5, max_length=2000)
    contact_email: EmailStr | None = None


class ReportOut(BaseModel):
    id: int
    status: str


class ClaimIn(BaseModel):
    claimant_email: EmailStr
    method: str = Field(default="meta_tag", pattern="^(meta_tag|manual)$")


class ClaimOut(BaseModel):
    claim_id: int
    method: str
    status: str
    token: str
    instructions: str


class VerifyIn(BaseModel):
    token: str


class VerifyOut(BaseModel):
    verified: bool
    detail: str
