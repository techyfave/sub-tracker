def build_recommendation_context(
    subscription: dict,
    usage: dict,
) -> dict:

    return {
        "subscription": {
            "id": subscription["id"],
            "name": subscription["name"],
            "monthly_cost": subscription["monthly_cost"],
            "currency": subscription["currency"],
        },
        "usage": {
            "frequency": usage["frequency"],
            "last_used": usage["last_used"],
        },
    }