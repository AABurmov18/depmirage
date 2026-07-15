"""Example app with intentionally-planted FAKE secrets for depmirage to catch.

None of these values are real credentials. They exist only so depmirage's
secret scanner has something to flag in the example folder. This file is a
deliberate anti-pattern — do not use it as a template.
"""

import os


# A fake OpenAI-style key — planted for the demo, not a real credential.
OPENAI_API_KEY = "sk-demo1234567890ABCDEFghijKLMNopqrSTUVwxyz0123"

# A fake AWS access key id — also planted, also not real.
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"


def make_client():
    # Prefer the environment; the hardcoded default above is the anti-pattern
    # depmirage is meant to flag.
    return os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)


if __name__ == "__main__":
    make_client()
