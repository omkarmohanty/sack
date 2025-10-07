from django.core.management.base import BaseCommand
from django.db import transaction
from resource_manager.models import ResourceUsage

class Command(BaseCommand):
    help = 'Cleanup duplicate active ResourceUsage entries per resource, keeping the most recent one.'

    def handle(self, *args, **options):
        self.stdout.write('Scanning for duplicate active usages...')
        duplicates = 0
        with transaction.atomic():
            # Find resources with multiple active usages
            active = ResourceUsage.objects.filter(is_active=True).order_by('resource_id', '-start_time')
            keep = set()
            to_deactivate = []
            for usage in active:
                key = usage.resource_id
                if key in keep:
                    # Mark this one as inactive (older than the most recent)
                    to_deactivate.append(usage)
                else:
                    keep.add(key)

            for u in to_deactivate:
                u.is_active = False
                u.end_time = u.start_time  # mark as ended at start to indicate invalid
                u.auto_released = True
                u.save()
                duplicates += 1

        self.stdout.write(self.style.SUCCESS(f'Cleanup complete. Deactivated {duplicates} duplicate active usages.'))
