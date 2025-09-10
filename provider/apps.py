from django.apps import AppConfig
from django.db.models.signals import post_migrate
import logging

logger = logging.getLogger(__name__)

class ProviderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'provider'

    # def ready(self):
    #     post_migrate.connect(create_periodic_tasks, sender=self)

# def create_periodic_tasks(sender, **kwargs):
#     from django_celery_beat.models import PeriodicTask, IntervalSchedule
#     import json

#     try:
#         schedule, _ = IntervalSchedule.objects.get_or_create(
#             every=10,
#             period=IntervalSchedule.SECONDS,
#         )

#         task, created = PeriodicTask.objects.get_or_create(
#             interval=schedule,
#             name='Run test_print_task every 10 seconds',
#             task='provider.tasks.test_print_task',
#             defaults={'args': json.dumps([])},
#         )

#         if created:
#             print("✅ Created periodic task: test_print_task")
#         else:
#             print("ℹ️ Periodic task already exists")

#     except Exception as e:
#         logger.error(f"❌ Error creating periodic task: {e}")
