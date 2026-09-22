def test_create_short_url(client, auth_headers):
    response = client.post(
        "/urls",
        headers=auth_headers,
        json={
            "original_url": "https://www.google.com/"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["original_url"] == "https://www.google.com/"
    assert "short_code" in data
    assert "short_url" in data

def test_user_cannot_access_another_users_analytics(client, auth_headers):
    # User 1 creates a URL
    create_response = client.post(
        "/urls",
        headers=auth_headers,
        json={
            "original_url": "https://www.google.com/"
        }
    )

    assert create_response.status_code == 200

    short_code = create_response.json()["short_code"]

    # Create a second user
    import uuid

    username = f"otheruser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "TestPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    other_token = login_response.json()["access_token"]

    other_headers = {
        "Authorization": f"Bearer {other_token}"
    }

    # User 2 tries to access User 1's analytics
    analytics_response = client.get(
        f"/urls/{short_code}/analytics",
        headers=other_headers
    )

    assert analytics_response.status_code == 403

def test_user_cannot_delete_another_users_url(client, auth_headers):
    # User 1 creates a URL
    create_response = client.post(
        "/urls",
        headers=auth_headers,
        json={
            "original_url": "https://www.google.com/"
        }
    )

    assert create_response.status_code == 200

    short_code = create_response.json()["short_code"]

    # Create User 2
    import uuid

    username = f"deleteuser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "TestPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    other_token = login_response.json()["access_token"]

    other_headers = {
        "Authorization": f"Bearer {other_token}"
    }

    # User 2 attempts to delete User 1's URL
    delete_response = client.delete(
        f"/urls/{short_code}",
        headers=other_headers
    )

    assert delete_response.status_code == 403

def test_owner_can_delete_url(client, auth_headers):
    create_response = client.post(
        "/urls",
        headers=auth_headers,
        json={
            "original_url": "https://www.example.com/"
        }
    )

    assert create_response.status_code == 200

    short_code = create_response.json()["short_code"]

    delete_response = client.delete(
        f"/urls/{short_code}",
        headers=auth_headers
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["short_code"] == short_code

    # Confirm the URL no longer exists
    analytics_response = client.get(
        f"/urls/{short_code}/analytics",
        headers=auth_headers
    )

    assert analytics_response.status_code == 404


def test_create_url_without_authentication(client):
    response = client.post(
        "/urls",
        json={
            "original_url": "https://www.example.com/"
        }
    )

    assert response.status_code == 401


def test_create_url_with_invalid_token(client):
    headers = {
        "Authorization": "Bearer invalid-token"
    }

    response = client.post(
        "/urls",
        headers=headers,
        json={
            "original_url": "https://www.example.com/"
        }
    )

    assert response.status_code == 401