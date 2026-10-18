"""
Listing data model.

Every listing carries *where the data came from* (ListingSource rows) and *how far we trust it*
(trust_tier). The public API only shows listings that are published and at or above
settings.PUBLIC_MIN_TIER, and only shows contact details once the owner verified the listing.
"""
import secrets

from django.conf import settings
from django.db import models


class TrustTier(models.IntegerChoices):
    UNVERIFIED = 0, "Unverified"
    SOURCE_LISTED = 1, "Listed by a source"          # e.g. found in OpenStreetMap
    REGISTRY_CHECKED = 2, "Registry checked"         # e.g. matched to a DOT accreditation / DTI / SEC record
    OWNER_VERIFIED = 3, "Owner verified"             # the owner proved control of the business website


class Category(models.TextChoices):
    ACCOMMODATION = "accommodation", "Accommodation"
    RESTAURANT = "restaurant", "Food & drink"
    TOUR_OPERATOR = "tour_operator", "Tour operator"
    TRAVEL_AGENCY = "travel_agency", "Travel agency"
    ATTRACTION = "attraction", "Attraction"
    ACTIVITY = "activity", "Activity & adventure"
    TRANSPORT = "transport", "Transport"
    ORGANIZATION = "organization", "Organization / tourism office"
    OTHER = "other", "Other"


class Source(models.Model):
    """A place we import data from. Carries the licence/attribution text we must show publicly."""

    class Kind(models.TextChoices):
        OSM = "osm", "OpenStreetMap"
        DOT = "dot", "Department of Tourism"
        LGU = "lgu", "Local government / tourism office"
        REGISTRY = "registry", "Business registry (DTI/SEC)"
        OWNER = "owner", "Submitted by owner"
        MANUAL = "manual", "Manual entry"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    url = models.URLField(blank=True)
    license = models.CharField(max_length=120, blank=True, help_text="e.g. ODbL 1.0")
    attribution = models.CharField(max_length=300, blank=True, help_text="Text shown next to data from this source.")
    default_tier = models.IntegerField(choices=TrustTier.choices, default=TrustTier.SOURCE_LISTED)
    auto_publish = models.BooleanField(default=False, help_text="Imported listings go live without manual review.")

    def __str__(self):
        return self.name


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (not public)"
        PUBLISHED = "published", "Published"
        HIDDEN = "hidden", "Hidden (reported / stale)"

    slug = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=120, blank=True)
    province = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    website = models.URLField(blank=True)
    # Business contact details. Only exposed publicly once the owner verified the listing.
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)

    trust_tier = models.IntegerField(choices=TrustTier.choices, default=TrustTier.SOURCE_LISTED)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    owner_email = models.EmailField(blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "trust_tier"]),
            models.Index(fields=["province", "category"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return self.name


class ListingSource(models.Model):
    """Provenance: which source said what about a listing, and when."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="sources")
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="listing_links")
    external_id = models.CharField(max_length=200, help_text="The source's own id, e.g. node/123456 for OSM.")
    source_url = models.URLField(blank=True)
    fetched_at = models.DateTimeField(auto_now=True)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "external_id"], name="uniq_source_external_id")]

    def __str__(self):
        return f"{self.source.slug}:{self.external_id}"


def _new_token() -> str:
    return secrets.token_urlsafe(24)


class Claim(models.Model):
    """A business owner asking to take over a listing."""

    class Method(models.TextChoices):
        META_TAG = "meta_tag", "Meta tag on the business website (automatic)"
        MANUAL = "manual", "Manual review (documents)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="claims")
    claimant_email = models.EmailField()
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.META_TAG)
    token = models.CharField(max_length=64, default=_new_token, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True, help_text="Reviewer notes, evidence seen.")
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self):
        return f"{self.listing} <- {self.claimant_email} ({self.status})"


class Report(models.Model):
    """'Report an error' from any visitor."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reports")
    message = models.TextField(max_length=2000)
    contact_email = models.EmailField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report on {self.listing} ({self.status})"
