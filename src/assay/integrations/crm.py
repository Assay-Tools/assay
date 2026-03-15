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


def get_contact(email: str) -> dict | None:
    """Look up a contact by email and return their CRM context as a plain dict.

    Returns None if the contact doesn't exist or CRM is unavailable.
    Intended for agent use — call this before sending any email to check
    do_not_contact status and understand relationship history.

    Returns dict with:
        found: True
        id, email, status, tags, notes, source, next_followup
        is_do_not_contact: bool — True if tagged do_not_contact or opted_out
    """
    store = _get_store()
    if not store:
        return None

    try:
        contact = store.find_by_email(email)
        if not contact:
            return None

        return {
            "found": True,
            "id": contact.id,
            "email": contact.email,
            "status": contact.status.value if hasattr(contact.status, "value") else str(contact.status),
            "tags": list(contact.tags or []),
            "notes": contact.notes or "",
            "source": contact.source or "",
            "next_followup": contact.next_followup.isoformat() if contact.next_followup else None,
            "is_do_not_contact": any(
                t in (contact.tags or []) for t in ["do_not_contact", "opted_out"]
            ),
        }
    except Exception:
        logger.warning("CRM: get_contact failed", exc_info=True)
        return None


def log_email_sent(email: str, subject: str, body_snippet: str = ""):
    """Log an outbound reply from the triage agent in the CRM.

    Call after successfully sending a reply from hello@assay.tools.
    Creates the contact if they don't exist yet (source=assay_outbound_email).
    """
    store = _get_store()
    if not store:
        return

    try:
        from incubator.crm.models import Contact, ContactStatus, Interaction, InteractionType

        contact = store.find_by_email(email)
        if not contact:
            contact = store.add_contact(Contact(
                email=email,
                source="assay_outbound_email",
                status=ContactStatus.NEW,
                notes=f"First contact via outbound triage email: {subject}",
            ))

        store.add_interaction(Interaction(
            contact_id=contact.id,
            type=InteractionType.EMAIL_SENT,
            direction="outbound",
            subject=subject,
            body=body_snippet[:500],
            agent="assay_triage",
        ))

        logger.info("CRM: logged outbound triage email to %s", email[:3] + "***")
    except Exception:
        logger.warning("CRM: failed to log outbound triage email", exc_info=True)


def mark_do_not_contact(email: str, reason: str = ""):
    """Mark a contact as do_not_contact in the CRM.

    Creates the contact if they don't exist. Adds 'do_not_contact' and
    'opted_out' tags, sets status=DISQUALIFIED, appends reason to notes.
    """
    store = _get_store()
    if not store:
        return

    try:
        from incubator.crm.models import Contact, ContactStatus, Interaction, InteractionType

        existing = store.find_by_email(email)
        if existing:
            tags = list(existing.tags or [])
            for t in ["do_not_contact", "opted_out"]:
                if t not in tags:
                    tags.append(t)
            notes = existing.notes or ""
            if reason:
                notes = f"{notes}\nOpt-out: {reason}".strip()
            store.update_contact(
                existing.id,
                tags=tags,
                status=ContactStatus.DISQUALIFIED.value,
                notes=notes,
            )
            contact_id = existing.id
        else:
            contact = Contact(
                email=email,
                source="assay_opt_out",
                status=ContactStatus.DISQUALIFIED,
                tags=["do_not_contact", "opted_out"],
                notes=f"Opt-out: {reason}" if reason else "Opted out",
            )
            contact = store.add_contact(contact)
            contact_id = contact.id

        store.add_interaction(Interaction(
            contact_id=contact_id,
            type=InteractionType.NOTE,
            direction="inbound",
            subject="Opt-out",
            body=reason or "Contact marked do_not_contact",
            agent="assay_triage",
        ))

        logger.info("CRM: marked %s as do_not_contact", email[:3] + "***")
    except Exception:
        logger.warning("CRM: failed to mark do_not_contact", exc_info=True)


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
