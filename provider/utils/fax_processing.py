from provider.services import faxage

PROVIDER_SERVICES = {
    "faxage": faxage.fetch_faxes_from_faxage,
    # add other providers here later
}

def process_user_providers_faxes(user):
    from provider.models import FaxProvider
    import traceback

    providers = FaxProvider.objects.filter(user=user, is_deleted=False)
    saved_paths_all = []

    for provider in providers:
        provider_key = provider.provider.lower()
        print(f"\n🔍 Processing faxes for provider: {provider_key} (username: {provider.username})")

        if provider_key in PROVIDER_SERVICES:
            service_func = PROVIDER_SERVICES[provider_key]
            try:
                saved_paths = service_func(provider) or []
                print(f"📄 Fetched and saved {len(saved_paths)} faxes for {provider.username}")
                saved_paths_all.extend(saved_paths)
            except Exception as e:
                print(f"❌ Error while processing faxes for provider '{provider.username}': {e}")
                traceback.print_exc()
        else:
            print(f"⚠️ No service found for provider '{provider.provider}' — skipping")

    return saved_paths_all
