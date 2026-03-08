"""CRM integration — syncs Assay events to the shared incubator CRM.

Uses the incubator.crm package (Firestore-backed, namespaced by business slug).
Gracefully degrades if the incubator package is not installed or Firestore
is not reachable — CRM failures never break Assay's core flow.

Auth: Application Default Credentials (GCP_PROJECT_ID=business-34-incubator).
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_CRM_AVAILABLE: bool | None = None


def _get_store():
    """Lazy-load CRM store. Returns None if unavailable."""
    global _CRM_AVAILABLE
    if _CRM_AVAILABLE is False:
        return None
    try:
        from incubator.crm.store import CRMStore
        store = CRMStore(slug="assay")
        _CRM_AVAILABLE = True
        return store
    except ImportError:
        if _CRM_AVAILABLE is None:
            logger.info("incubator.crm not installed — CRM integration disabled")
        _CRM_AVAILABLE = False
        return None
    except Exception:
        logger.warning("CRM store init failed — CRM integration disabled", exc_info=True)
        _CRM_AVAILABLE = False
        return None


def _product_tag(order_type: str) -> str:
    """Map Assay order types to CRM tags."""
    return {
        "report": "full_report",
        "brief": "package_brief",
        "monitoring_subscription": "monitoring",
    }.get(order_type, order_type)


def on_purchase(email: str, order_type: str, package_id: str, order_id: int):
    """Record a purchase in the CRM.

    Creates or updates a Contact with status=CUSTOMER and tags with
    the product purchased. For monitoring subscriptions, sets a 30-day
    follow-up for check-in.
    """
    store = _get_store()
    if not store:
        return

    try:
        from incubator.crm.models import Contact, ContactStatus, Interaction, InteractionType

        tag = _product_tag(order_type)
        existing = store.find_by_email(email)

        if existing:
            # Update existing contact: ensure CUSTOMER status, add product tag
            updates = {"status": ContactStatus.CUSTOMER.value}
            tags = list(existing.tags)
            if tag not in tags:
                tags.append(tag)
                updates["tags"] = tags
            if order_type == "monitoring_subscription":
                updates["next_followup"] = datetime.now(timezone.utc) + timedelta(days=30)
            store.update_contact(existing.id, **updates)
            contact_id = existing.id
        else:
            # New contact from purchase
            contact = Contact(
                email=email,
                source="assay_purchase",
                status=ContactStatus.CUSTOMER,
                tags=[tag],
                notes=f"First purchase: {order_type} for {package_id} (order #{order_id})",
                next_followup=(
                    datetime.now(timezone.utc) + timedelta(days=30)
                    if order_type == "monitoring_subscription"
                    else None
                ),
            )
            contact = store.add_contact(contact)
            contact_id = contact.id

        # Log the purchase as an interaction
        store.add_interaction(Interaction(
            contact_id=contact_id,
            type=InteractionType.NOTE,
            direction="inbound",
            subject=f"Purchase: {order_type}",
            body=f"Purchased {order_type} for {package_id} (order #{order_id})",
            agent="assay",
        ))

        logger.info("CRM: recorded purchase for %s (order #%d)", email[:3] + "***", order_id)
    except Exception:
        logger.warning("CRM: failed to record purchase for order #%d", order_id, exc_info=True)


def on_score_change_alert_sent(email: str, package_id: str):
    """Log a score change alert email as an interaction in the CRM."""
    store = _get_store()
    if not store:
        return

    try:
        from incubator.crm.models import Interaction, InteractionType

        contact = store.find_by_email(email)
        if not contact:
            return  # Don't create contacts from alert sends

        store.add_interaction(Interaction(
            contact_id=contact.id,
            type=InteractionType.EMAIL_SENT,
            direction="outbound",
            subject=f"Score change alert: {package_id}",
            body=f"Automated score change notification for {package_id}",
            agent="assay",
        ))
    except Exception:
        logger.warning("CRM: failed to log score change alert for %s", package_id, exc_info=True)


def on_email_received(email: str, subject: str, body_snippet: str = ""):
    """Log an inbound support email as an interaction in the CRM.

    Call this from the email triage pipeline when processing inbound
    messages to hello@assay.tools.
    """
    store = _get_store()
    if not store:
        return

    try:
        from incubator.crm.models import Contact, ContactStatus, Interaction, InteractionType

        contact = store.find_by_email(email)
        if not contact:
            # Create a new contact from inbound email
            contact = store.add_contact(Contact(
                email=email,
                source="assay_inbound_email",
                status=ContactStatus.NEW,
                notes=f"First contact via inbound email: {subject}",
            ))

        store.add_interaction(Interaction(
            contact_id=contact.id,
            type=InteractionType.EMAIL_RECEIVED,
            direction="inbound",
            subject=subject,
            body=body_snippet[:500],  # Cap snippet length
            agent="assay",
        ))

        logger.info("CRM: recorded inbound email from %s", email[:3] + "***")
    except Exception:
        logger.warning("CRM: failed to log inbound email", exc_info=True)


def on_newsletter_signup(email: str):
    """Record a newsletter signup in the CRM.

    Creates a NEW contact if not already known, or adds the
    'newsletter' tag to an existing contact.
    """
    store = _get_store()
    if not store:
        return

    try:
        from incubator.crm.models import Contact, ContactStatus

        existing = store.find_by_email(email)
        if existing:
            tags = list(existing.tags)
            if "newsletter" not in tags:
                tags.append("newsletter")
                store.update_contact(existing.id, tags=tags)
        else:
            store.add_contact(Contact(
                email=email,
                source="assay_signup",
                status=ContactStatus.NEW,
                tags=["newsletter"],
            ))

        logger.info("CRM: recorded newsletter signup for %s", email[:3] + "***")
    except Exception:
        logger.warning("CRM: failed to record newsletter signup", exc_info=True)
