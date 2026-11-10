from enum import StrEnum


class RecommendationAction(StrEnum):
    KEEP = "keep"
    DOWNGRADE = "downgrade"
    CANCEL = "cancel"
    REVIEW = "review"