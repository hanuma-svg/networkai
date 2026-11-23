import inngest
from src.config import settings

# Initialize Inngest client
# Works in dev mode (when signing key is unset) and production mode
inngest_client = inngest.Inngest(
    app_id="networkai",
    is_production=bool(settings.INNGEST_SIGNING_KEY),
    signing_key=settings.INNGEST_SIGNING_KEY,
    event_key=settings.INNGEST_EVENT_KEY,
)
