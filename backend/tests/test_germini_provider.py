import asyncio

from dotenv import load_dotenv

from app.infrastructure.ai.germini_provider import GeminiProvider


async def main():
    load_dotenv()

    provider = GeminiProvider()

    context = {
        "subscription": {
            "name": "Netflix",
            "monthly_cost": 10000,
            "currency": "NGN",
            "current_plan": "Premium",
        }
    }

    try:
        result = await provider.generate(context)

        print("GEMINI RESPONSE:")
        print(result)

    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())