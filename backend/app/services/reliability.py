"""Domain reliability score calculator.

Computes a 0.0–1.0 reliability score for a news domain based on
multiple signals: trust score, paywall presence, and user feedback.
"""

import structlog
from sqlalchemy import select, func
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


def compute_reliability_score(
    trust_score: int | None,
    has_paywall: bool,
    paywall_hits_count: int,
    likes: int = 0,
    dislikes: int = 0,
) -> float:
    """
    Compute a reliability score (0.0 – 1.0) for a domain.

    Algorithm:
    - Base: trust_score / 100 (if evaluated), else 0.5 neutral
    - Paywall penalty: -0.25 if has_paywall, scaled by hit count (max -0.35)
    - Feedback adjustment: +0.05 per like, -0.08 per dislike (capped)
    - Final: clamped to [0.0, 1.0]

    Paywall is heavily weighted because it structurally degrades analysis quality.
    """
    # Base score from AI trust evaluation
    if trust_score is not None:
        base = trust_score / 100.0
    else:
        base = 0.5  # unknown domain = neutral

    # Paywall penalty (very deterministic on quality)
    paywall_penalty = 0.0
    if has_paywall:
        # Base penalty + incremental per hit (caps at -0.35)
        paywall_penalty = min(0.25 + (paywall_hits_count * 0.02), 0.35)

    # Feedback adjustment
    feedback_bonus = (likes * 0.05) - (dislikes * 0.08)
    # Cap feedback effect to ±0.2
    feedback_bonus = max(-0.2, min(0.2, feedback_bonus))

    score = base - paywall_penalty + feedback_bonus
    return round(max(0.0, min(1.0, score)), 2)


def update_domain_reliability(session: Session, domain: str) -> float | None:
    """
    Recalculate and persist the reliability score for a domain.
    Returns the new score, or None if domain not found.
    """
    from app.models.domain import SourceDomain, Feedback

    stmt = select(SourceDomain).where(SourceDomain.domain == domain)
    domain_entry = session.execute(stmt).scalar_one_or_none()

    if not domain_entry:
        return None

    # Count feedback for this domain
    likes_stmt = select(func.count()).select_from(Feedback).where(
        Feedback.target_type == "domain",
        Feedback.target_id == domain,
        Feedback.vote == "like",
    )
    dislikes_stmt = select(func.count()).select_from(Feedback).where(
        Feedback.target_type == "domain",
        Feedback.target_id == domain,
        Feedback.vote == "dislike",
    )

    likes = session.execute(likes_stmt).scalar() or 0
    dislikes = session.execute(dislikes_stmt).scalar() or 0

    new_score = compute_reliability_score(
        trust_score=domain_entry.trust_score,
        has_paywall=domain_entry.has_paywall,
        paywall_hits_count=domain_entry.paywall_hits_count,
        likes=likes,
        dislikes=dislikes,
    )

    domain_entry.reliability_score = new_score
    session.commit()

    logger.info(
        "Domain reliability updated",
        domain=domain,
        reliability_score=new_score,
        trust_score=domain_entry.trust_score,
        has_paywall=domain_entry.has_paywall,
        paywall_hits=domain_entry.paywall_hits_count,
        likes=likes,
        dislikes=dislikes,
    )

    return new_score
