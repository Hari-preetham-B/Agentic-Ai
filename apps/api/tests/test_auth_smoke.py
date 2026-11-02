"""Real Supabase Auth smoke test (manual, not part of pytest).

This script verifies end-to-end authentication with a real Supabase backend.
It is NOT run by pytest — execute it manually when Supabase credentials are
configured:

    cd apps/api
    python tests/test_auth_smoke.py

Prerequisites:
- SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY configured in .env
- A valid Supabase Auth access token obtained through the normal frontend
  sign-in flow (or a controlled local test mechanism)

Security:
- Never prints the access token or any credentials.
- Only sends the token to the local backend over HTTP.
"""

from __future__ import annotations

import os
import sys

import httpx


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        print("ERROR: SUPABASE_URL not set in environment.", file=sys.stderr)
        sys.exit(1)

    print("CareerTwin Real Auth Smoke Test")
    print("=" * 40)

    # Step 1: Prompt for a Supabase Auth access token.
    # The user obtains this through the normal frontend sign-in flow.
    # We never print or log the token value.
    print(
        "\n1. Obtain a Supabase Auth access token from the frontend sign-in flow."
    )
    print("   Then paste it below (input is NOT echoed).")
    import getpass

    token = getpass.getpass("Access Token: ")
    if not token:
        print("ERROR: No token provided.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Send the token to a protected FastAPI endpoint.
    api_url = os.environ.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")
    protected_endpoint = f"{api_url.rstrip('/')}/auth/me"

    print("\n2. Sending token to protected endpoint...")
    print(f"   POST {protected_endpoint}")
    print("   (token value is NOT printed)")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                protected_endpoint,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.ConnectError:
        print(
            "ERROR: Could not connect to backend. Is the server running?",
            file=sys.stderr,
        )
        sys.exit(1)

    # Step 3: Verify the response.
    if response.status_code == 200:
        data = response.json()
        user_id = data.get("user_id")
        email = data.get("email")
        print("\n3. Authentication successful!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print("\nSmoke test PASSED: backend recognizes Supabase user identity.")
    elif response.status_code == 401:
        print("\n3. Authentication rejected (401 Unauthorized).")
        print("   The token may be invalid or expired.")
        print("\nSmoke test FAILED: backend did not accept the token.")
        sys.exit(1)
    else:
        print(f"\n3. Unexpected response: {response.status_code}")
        print("\nSmoke test FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
