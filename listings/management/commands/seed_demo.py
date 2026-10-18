"""Creates a handful of clearly-labelled demo listings so the API and admin have something to show."""
from django.core.management.base import BaseCommand

from listings.models import Category, Source, TrustTier
from listings.services import upsert_listing


class Command(BaseCommand):
    help = "Seed demo sources and listings (development only)."

    def handle(self, *args, **options):
        osm, _ = Source.objects.get_or_create(
            slug="osm",
            defaults=dict(
                name="OpenStreetMap", kind=Source.Kind.OSM, url="https://www.openstreetmap.org/copyright",
                license="ODbL 1.0", attribution="© OpenStreetMap contributors",
                default_tier=TrustTier.SOURCE_LISTED, auto_publish=True,
            ),
        )
        demo = [
            ("node/1", dict(name="Demo Beach Resort", category=Category.ACCOMMODATION, city="Moalboal", province="Cebu",
                            region="Central Visayas", latitude=9.9496, longitude=123.3957, website="https://example.com")),
            ("node/2", dict(name="Demo Island Tours", category=Category.TOUR_OPERATOR, city="El Nido", province="Palawan",
                            region="MIMAROPA", latitude=11.1784, longitude=119.3935)),
        ]
        for ext, data in demo:
            _, created = upsert_listing(osm, ext, data, source_url=f"https://www.openstreetmap.org/{ext}")
            self.stdout.write(f"{'created' if created else 'updated'} {data['name']}")
