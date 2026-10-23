import backend


def fresh_db(tmp_path):
    backend.DB = tmp_path / "test.sqlite"
    backend.init_db()


def csrf(client):
    response = client.get("/api/csrf")
    assert response.status_code == 200, response.get_json()
    return {"X-CSRF-Token": response.get_json()["csrf_token"]}


def client_post(client, path, payload):
    return client.post(path, json=payload, headers=csrf(client))


def register_client(client, name, phone):
    response = client.post("/api/client/register", json={"name": name, "phone": phone})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def owner(client):
    # The real owner flow is device-bound; use developer auth only to test
    # owner-authorized appointment routes against a temporary database.
    response = client.post("/api/dev/login", json={"password": backend.get_dev_secret()})
    assert response.status_code == 200, response.get_json()
    csrf(client)


def create_appointment(client, phone, service_id, date, time):
    return client_post(
        client,
        "/api/appointments",
        {"phone": phone, "service_id": service_id, "date": date, "time": time},
    )


def test_pending_confirm_and_notifications(tmp_path):
    fresh_db(tmp_path)
    client = backend.app.test_client()
    register_client(client, "A", "+351910000201")
    response = create_appointment(client, "+351910000201", 1, "2026-10-30", "15:00")
    assert response.status_code == 201, response.get_json()
    appointment_id = response.get_json()["id"]

    owner(client)
    assert client.get("/api/owner/appointments?status=pending").status_code == 200
    response = client_post(client, f"/api/owner/appointments/{appointment_id}/confirm", {})
    assert response.status_code == 200, response.get_json()
    notifications = client.get("/api/notifications")
    assert notifications.status_code == 200, notifications.get_json()
    assert {item["channel"] for item in notifications.get_json()
            if item["appointment_id"] == appointment_id} == {"whatsapp", "sms"}


def test_same_slot_cannot_be_confirmed_twice_and_cancel_releases(tmp_path):
    fresh_db(tmp_path)
    first = backend.app.test_client()
    second = backend.app.test_client()
    owner_client = backend.app.test_client()
    register_client(first, "A", "+351910000211")
    register_client(second, "B", "+351910000212")

    first_response = create_appointment(first, "+351910000211", 1, "2026-10-31", "16:00")
    second_response = create_appointment(second, "+351910000212", 1, "2026-10-31", "16:00")
    assert first_response.status_code == 201, first_response.get_json()
    assert second_response.status_code == 201, second_response.get_json()
    first_id = first_response.get_json()["id"]
    second_id = second_response.get_json()["id"]

    owner(owner_client)
    response = client_post(owner_client, f"/api/owner/appointments/{first_id}/confirm", {})
    assert response.status_code == 200, response.get_json()
    response = client_post(owner_client, f"/api/owner/appointments/{second_id}/confirm", {})
    assert response.status_code == 409, response.get_json()
    response = client_post(second, f"/api/appointments/{first_id}/cancel", {})
    assert response.status_code == 403, response.get_json()
    response = client_post(first, f"/api/appointments/{first_id}/cancel", {})
    assert response.status_code == 200, response.get_json()
    response = client_post(owner_client, f"/api/owner/appointments/{second_id}/confirm", {})
    assert response.status_code == 200, response.get_json()


def test_reject_and_separate_owner_page(tmp_path):
    fresh_db(tmp_path)
    client = backend.app.test_client()
    register_client(client, "C", "+351910000221")
    response = create_appointment(client, "+351910000221", 2, "2026-11-01", "10:00")
    assert response.status_code == 201, response.get_json()
    appointment_id = response.get_json()["id"]
    owner(client)
    response = client_post(client, f"/api/owner/appointments/{appointment_id}/reject", {})
    assert response.status_code == 200, response.get_json()
    notifications = client.get("/api/notifications")
    assert notifications.status_code == 200, notifications.get_json()
    assert {item["channel"] for item in notifications.get_json()
            if item["appointment_id"] == appointment_id} == {"whatsapp", "sms"}
    assert "Sou proprietario" not in client.get("/").get_data(as_text=True)
    assert client.get("/proprietario.html").status_code == 200


def test_client_idor_is_blocked(tmp_path):
    fresh_db(tmp_path)
    first = backend.app.test_client()
    second = backend.app.test_client()
    register_client(first, "A", "+351910000231")
    register_client(second, "B", "+351910000232")
    response = create_appointment(second, "+351910000232", 1, "2026-11-02", "11:00")
    assert response.status_code == 201, response.get_json()
    appointment_id = response.get_json()["id"]
    assert first.get("/api/appointments?phone=%2B351910000232").status_code == 403
    response = client_post(first, f"/api/appointments/{appointment_id}/cancel", {})
    assert response.status_code == 403


def test_duplicate_client_registration_is_blocked(tmp_path):
    fresh_db(tmp_path)
    first = backend.app.test_client()
    second = backend.app.test_client()
    register_client(first, "A", "+351910000241")
    response = second.post("/api/client/register",
                           json={"name": "ATTACKER", "phone": "+351910000241"})
    assert response.status_code == 409, response.get_json()
