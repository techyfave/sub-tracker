from app.domain.recommendations.schema import (
    RecommendationContract,
)


class RecommendationPipeline:

    def __init__(
        self,
        provider,
        context_builder,
        grounding_validator,
        policy_validator,
    ):
        self.provider = provider
        self.context_builder = context_builder
        self.grounding_validator = grounding_validator
        self.policy_validator = policy_validator

    async def generate(
        self,
        subscription,
        usage,
        allowed_evidence,
        system_prompt,
    ):

        context = self.context_builder(
            subscription,
            usage,
        )

        user_prompt = str(context)

        for attempt in range(3):

            raw_output = await self.provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            try:
                recommendation = (
                    RecommendationContract.model_validate_json(
                        raw_output
                    )
                )

                self.grounding_validator(
                    recommendation,
                    allowed_evidence,
                )

                self.policy_validator(
                    recommendation,
                    subscription,
                    usage,
                )

                return recommendation

            except ValueError as exc:
                if attempt == 2:
                    raise RuntimeError(
                        "Recommendation pipeline exhausted retries"
                    ) from exc

                user_prompt = (
                    f"{context}\n"
                    f"Your previous output failed validation: {exc}\n"
                    "Return a corrected structured response."
                )

        raise RuntimeError("Recommendation generation failed")