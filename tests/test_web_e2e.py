from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT = Path(__file__).resolve().parents[1]
API_PREFIX = "https://barbearia-api-w37o.onrender.com/api"
APPOINTMENT = {
    "id": 1, "date": "2026-11-20", "time": "15:00", "status": "pending",
    "client": "Ana Teste", "phone": "+351910000001",
    "service": "Corte de Cabelo", "service_id": 1, "price": 15, "duration": 30,
}


def mock_api(route):
    request = route.request
    path = request.url.split("/api", 1)[-1].split("?", 1)[0]
    method = request.method
    if method == "GET" and path == "/services":
        data, status = [{"id": 1, "name": "Corte de Cabelo", "price": 15, "duration": 30}], 200
    elif method == "POST" and path == "/client/register":
        data, status = {"id": 1, "name": "Ana Teste", "phone": "+351910000001"}, 200
    elif method == "GET" and path == "/csrf":
        data, status = {"csrf_token": "e2e-csrf-token"}, 200
    elif method == "POST" and path == "/appointments":
        data, status = APPOINTMENT, 201
    elif method == "GET" and path == "/appointments":
        data, status = [APPOINTMENT], 200
    elif method == "POST" and path.endswith("/cancel"):
        data, status = {"id": 1, "status": "cancelled"}, 200
    elif method == "POST" and path == "/owner/challenge":
        data, status = {"challenge": "dGVzdC1jaGFsbGVuZ2U"}, 200
    elif method == "POST" and path == "/owner/login":
        data, status = {"authenticated": True, "phone": "+351920000002"}, 200
    elif method == "GET" and path == "/owner/appointments":
        data, status = [APPOINTMENT], 200
    elif method == "GET" and path == "/owner/clients":
        data, status = [{"name": "Ana Teste", "phone": "+351910000001", "appointments": 1}], 200
    elif method == "GET" and path == "/availability":
        data, status = {"date": "2026-11-20", "available_slots": ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"], "occupied_slots": []}, 200
    elif method == "GET" and path == "/version":
        data, status = {"version": "1.0.0", "changelog": "Versão inicial"}, 200
    else:
        data, status = {"error": f"Unexpected mocked API request: {method} {path}"}, 404
    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))


def test_barbearia_client_and_owner_ui_smoke():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route(f"{API_PREFIX}/**", mock_api)

        page.goto((ROOT / "web" / "index.html").as_uri())
        page.evaluate("localStorage.clear()")
        page.reload()
        assert page.locator('[data-screen="welcome"]').is_visible()

        page.click('[data-go="register"]')
        page.fill("#regName", "Ana Teste")
        page.fill("#regPhone", "+351910000001")
        page.click("#registerBtn")
        page.locator('[data-screen="home"]').wait_for(state="visible")
        assert "Ana Teste" in page.locator("#hello").inner_text()

        page.click('[data-go="service"]')
        page.locator('input[name="service"][value="1"]').wait_for()
        page.check('input[name="service"][value="1"]')
        page.click('[data-next="datetime"]')
        page.locator("#times button").nth(0).click()
        page.locator("#date").fill("2026-11-20")
        page.click('[data-next="confirm"]')
        page.click("#confirmBtn")
        page.locator('[data-screen="success"]').wait_for(state="visible")

        page.locator('[data-screen="success"] [data-go="history"]').click()
        page.locator("#list").get_by_text("Corte de Cabelo").wait_for(state="visible")
        page.locator('[data-screen="history"] [data-go="home"]').click()
        page.locator('[data-screen="home"] [data-go="profile"]').first.click()
        assert "Ana Teste" in page.locator("#profileData").inner_text()

        page.goto((ROOT / "web" / "proprietario.html").as_uri())
        page.fill("#ownerPhone", "+351920000002")
        page.click("#ownerEnter")
        page.locator("#ownerArea").wait_for(state="visible")
        page.locator("#clients").get_by_text("Ana Teste").wait_for(state="visible")
        page.locator("#pending").get_by_text("Corte de Cabelo").wait_for(state="visible")
        browser.close()
