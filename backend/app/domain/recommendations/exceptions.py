class RecommendationDomainError(Exception):
    """Base exception for recommendation domain errors."""

    # no extra behaviour needed
    pass


class RecommendationNotFoundError(RecommendationDomainError):
    """Raised when a recommendation does not exist for the caller."""

    # build a readable message from the id
    def __init__(self, recommendation_id: str):
        # pass the message to the base Exception
        super().__init__(f"Recommendation with ID '{recommendation_id}' was not found.")
