"""Management command to create sample resources and users"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from resource_manager.models import Resource

class Command(BaseCommand):
    help = 'Create sample data for SACK Tool'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=5, help='Number of users to create')
        parser.add_argument('--resources', type=int, default=10, help='Number of resources to create')

    def handle(self, *args, **options):
        # Create superuser if not exists
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@sack.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Created superuser: admin/admin123'))

        # Create sample users
        for i in range(1, options['users'] + 1):
            username = f'user{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@sack.com',
                    password='password123'
                )
                self.stdout.write(self.style.SUCCESS(f'Created user: {username}/password123'))

        # Create sample resources
        resource_types = ['Windows', 'Ubuntu', 'Linux']
        base_ips = ['107.109.113.', '107.108.83.', '107.108.59.', '107.108.221.', '107.109.114.']

        for i in range(1, options['resources'] + 1):
            pc_name = f"{'Windows' if i % 3 == 0 else 'Ubuntu' if i % 2 == 0 else 'Linux'} {239 + i}"
            ip_base = base_ips[i % len(base_ips)]
            ip_address = f"{ip_base}{239 + i}"
            resource_type = resource_types[i % len(resource_types)]

            if not Resource.objects.filter(ip_address=ip_address).exists():
                resource = Resource.objects.create(
                    pc_name=pc_name.strip(),
                    ip_address=ip_address,
                    resource_type=resource_type,
                    status='Available',
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f'Created resource: {resource.pc_name} ({resource.ip_address})'))

        self.stdout.write(self.style.SUCCESS('\nSample data created successfully!'))