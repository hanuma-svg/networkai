import httpx
import uuid
from typing import Any, Dict, Optional
from src.config import settings
from src.models.schemas import PublishPostResponse


class LinkedInPublisherService:
    """Official LinkedIn Posts API client using OAuth w_member_social.
    
    Publishes approved or scheduled posts directly to the member's LinkedIn feed
    via POST https://api.linkedin.com/rest/posts.
    """

    API_URL = "https://api.linkedin.com/rest/posts"
    API_VERSION = "202401"

    def __init__(self, default_token: Optional[str] = None, default_author: Optional[str] = None):
        self.default_token = default_token or settings.LINKEDIN_ACCESS_TOKEN
        self.default_author = default_author or settings.LINKEDIN_AUTHOR_URN

    def publish_post(
        self,
        commentary: str,
        author_urn: Optional[str] = None,
        access_token: Optional[str] = None,
        visibility: str = "PUBLIC"
    ) -> PublishPostResponse:
        """Publishes commentary to LinkedIn feed via official REST API."""
        token = access_token or self.default_token
        author = author_urn or self.default_author or "urn:li:person:me"

        # Construct official LinkedIn REST Posts payload
        payload: Dict[str, Any] = {
            "author": author,
            "commentary": commentary,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": self.API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        # If token is provided, attempt live HTTP call
        if token and token != "mock_token":
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(self.API_URL, json=payload, headers=headers)
                    if resp.status_code in (201, 200):
                        post_urn = resp.headers.get("x-restli-id") or resp.json().get("id") or f"urn:li:share:{uuid.uuid4().hex[:12]}"
                        return PublishPostResponse(
                            status="success",
                            post_urn=post_urn,
                            lifecycle_state="PUBLISHED",
                            details={"headers": dict(resp.headers), "data": resp.json() if resp.content else {}}
                        )
                    else:
                        # Log error and return failure or fallback details
                        return PublishPostResponse(
                            status="api_error",
                            post_urn="",
                            lifecycle_state="FAILED",
                            details={"status_code": resp.status_code, "body": resp.text}
                        )
            except Exception as exc:
                return PublishPostResponse(
                    status="connection_error",
                    post_urn="",
                    lifecycle_state="FAILED",
                    details={"error": str(exc)}
                )

        # Simulation / Dry-run mode for testing and developer preview
        simulated_urn = f"urn:li:share:{uuid.uuid4().hex[:10]}"
        return PublishPostResponse(
            status="simulated",
            post_urn=simulated_urn,
            lifecycle_state="PUBLISHED",
            details={
                "message": "Published via simulated LinkedIn client (add LINKEDIN_ACCESS_TOKEN for live sync)",
                "payload_dispatched": payload,
            }
        )


linkedin_publisher = LinkedInPublisherService()
