from tests.conftest import register_login


def test_register_and_login(client):
    h = register_login(client, "a@x.com")
    me = client.get("/api/users/me", headers=h).json()
    assert me["email"] == "a@x.com" and me["role"] == "farmer" and "password" not in str(me)


def test_duplicate_registration(client):
    register_login(client, "a@x.com")
    r = client.post("/api/auth/register", json={"full_name": "Dup", "email": "A@x.com", "password": "Passw0rd!x"})
    assert r.status_code == 409


def test_invalid_credentials(client):
    register_login(client, "a@x.com")
    r = client.post("/api/auth/login", json={"email": "a@x.com", "password": "wrong-pass1"})
    assert r.status_code == 401


def test_cannot_self_register_as_admin(client):
    r = client.post("/api/auth/register", json={"full_name": "Eve", "email": "e@x.com",
                                                "password": "Passw0rd!x", "role": "admin"})
    assert r.status_code == 422


def test_vet_requires_license(client):
    r = client.post("/api/auth/register", json={"full_name": "Dr X", "email": "v@x.com",
                                                "password": "Passw0rd!x", "role": "veterinarian"})
    assert r.status_code == 422


def test_weak_password_rejected(client):
    r = client.post("/api/auth/register", json={"full_name": "Weak", "email": "w@x.com", "password": "abcdefgh"})
    assert r.status_code == 422


def test_unauthenticated_and_bad_token(client):
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/users/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_role_authorization(client, farmer, vet, admin):
    assert client.get("/api/admin/users", headers=farmer).status_code == 403
    assert client.get("/api/admin/users", headers=vet).status_code == 403
    assert client.get("/api/admin/users", headers=admin).status_code == 200
    assert client.get("/api/veterinary/cases", headers=farmer).status_code == 403
    assert client.post("/api/poultry", json={"poultry_type": "Chicken"}, headers=vet).status_code == 403


def test_deactivated_user_cannot_login(client, farmer, admin):
    uid = client.get("/api/users/me", headers=farmer).json()["user_id"]
    assert client.put(f"/api/admin/users/{uid}", json={"is_active": False}, headers=admin).status_code == 200
    assert client.get("/api/users/me", headers=farmer).status_code == 401
    assert client.post("/api/auth/login", json={"email": "farmer@test.com", "password": "Passw0rd!x"}).status_code == 403
