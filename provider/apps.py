from django.apps import AppConfig
from django.db.models.signals import post_migrate
import logging

logger = logging.getLogger(__name__)

class ProviderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'provider'
