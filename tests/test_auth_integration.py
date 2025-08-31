import os
import pytest
import requests


def _get_creds():
    email = os.getenv("AC9_TEST_EMAIL")
    pwd = os.getenv("AC9_TEST_PASSWORD")
    base = os.getenv("AC9_API_BASE", "https://ac9-sport-api.onrender.com")
    return base, email, pwd


@pytest.mark.skipif(
    not (os.getenv("AC9_TEST_EMAIL") and os.getenv("AC9_TEST_PASSWORD")),
    reason="Integration creds not set",
)
def test_live_login_prints_response():
    base, email, pwd = _get_creds()
    url = f"{base}/auth/login"
    headers = {
        "Origin": "https://www.ac9sport.com",
        "Content-Type": "application/json",
    }
    payload = {"email": email, "password": pwd}

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    print("STATUS:", resp.status_code)
    print("HEADERS:")
    for k, v in resp.headers.items():
        print(f"{k}: {v}")
    print("BODY:")
    print(resp.text)

    # Basic expectations for a successful auth: not 422
    assert resp.status_code != 422
