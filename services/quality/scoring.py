"""Quality issue severity and deterministic scoring."""

SEVERITY = {
    "SQLITE_INTEGRITY_FAILURE": "CRITICAL",
    "INVALID_EVENT_PAYLOAD": "HIGH",
    "UNKNOWN_CUSTOMER": "HIGH",
    "INVALID_CUSTOMER_DATE_RANGE": "HIGH",
    "EVENT_VOLUME_ANOMALY": "MEDIUM",
    "MULTI_CUSTOMER_SESSION": "MEDIUM",
    "EMPTY_SESSION_ID": "MEDIUM",
    "POTENTIAL_DUPLICATE_ACTIVITY": "LOW",
    "INSUFFICIENT_HISTORY": "INFO",
}

WEIGHTS = {
    "CRITICAL": 25,
    "HIGH": 10,
    "MEDIUM": 5,
    "LOW": 1,
    "INFO": 0,
}


def classify_issue(code):
    if code in SEVERITY:
        return SEVERITY[code]

    if code.endswith("_MISMATCH") or code.startswith("INVALID_"):
        return "MEDIUM"

    return "MEDIUM"


def score_quality(issues, total_events):
    """Score issues without penalizing informational findings."""
    if total_events < 0:
        raise ValueError("total_events cannot be negative")

    classified = []
    penalty = 0

    for issue in issues:
        item = dict(issue)
        severity = classify_issue(item["issue"])
        item["severity"] = severity
        classified.append(item)
        penalty += WEIGHTS[severity]

    denominator = max(total_events, 1)
    score = max(0.0, 100.0 - (penalty / denominator * 100.0))

    if any(item["severity"] == "CRITICAL" for item in classified):
        score = 0.0

    if score >= 95:
        grade = "EXCELLENT"
    elif score >= 85:
        grade = "GOOD"
    elif score >= 70:
        grade = "WARNING"
    else:
        grade = "CRITICAL"

    return {
        "quality_score": round(score, 2),
        "grade": grade,
        "severity_counts": {
            severity: sum(
                item["severity"] == severity
                for item in classified
            )
            for severity in WEIGHTS
        },
        "classified_issues": classified,
    }
