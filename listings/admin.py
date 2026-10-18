from django.contrib import admin, messages

from .models import Claim, Listing, ListingSource, Report, Source
from .services import approve_claim


class ListingSourceInline(admin.TabularInline):
    model = ListingSource
    extra = 0
    readonly_fields = ("fetched_at",)
    raw_id_fields = ("source",)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "license", "default_tier", "auto_publish")


@admin.action(description="Publish selected listings")
def publish(modeladmin, request, queryset):
    queryset.update(status=Listing.Status.PUBLISHED)


@admin.action(description="Hide selected listings")
def hide(modeladmin, request, queryset):
    queryset.update(status=Listing.Status.HIDDEN)


@admin.action(description="Mark as registry checked (you matched a DOT/DTI/SEC record)")
def mark_registry_checked(modeladmin, request, queryset):
    from django.utils import timezone

    queryset.filter(trust_tier__lt=2).update(trust_tier=2, last_verified_at=timezone.now())


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "province", "trust_tier", "status", "last_verified_at")
    list_filter = ("status", "trust_tier", "category", "province")
    search_fields = ("name", "city", "province", "website")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ListingSourceInline]
    actions = [publish, hide, mark_registry_checked]


@admin.action(description="Approve selected claims (promotes the listing to owner-verified)")
def approve(modeladmin, request, queryset):
    done = 0
    for claim in queryset.filter(status=Claim.Status.PENDING):
        approve_claim(claim, reviewer=request.user)
        done += 1
    modeladmin.message_user(request, f"{done} claim(s) approved.", messages.SUCCESS)


@admin.action(description="Reject selected claims")
def reject(modeladmin, request, queryset):
    queryset.filter(status=Claim.Status.PENDING).update(status=Claim.Status.REJECTED, reviewed_by=request.user)


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("listing", "claimant_email", "method", "status", "created_at")
    list_filter = ("status", "method")
    readonly_fields = ("token", "created_at", "verified_at")
    raw_id_fields = ("listing",)
    actions = [approve, reject]


@admin.action(description="Mark selected reports resolved")
def resolve(modeladmin, request, queryset):
    queryset.update(status=Report.Status.RESOLVED)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("listing", "status", "created_at", "contact_email")
    list_filter = ("status",)
    raw_id_fields = ("listing",)
    actions = [resolve]
