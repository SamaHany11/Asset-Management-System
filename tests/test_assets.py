import io
import json


def create_asset(client, auth_headers, **overrides):
    payload = {
        "type": "domain",
        "value": "example.com",
        "status": "active",
        "source": "scan",
        "tags": ["root"],
        "metadata_json": {},
    }
    payload.update(overrides)
    response = client.post("/assets", json=payload, headers=auth_headers)
    return response


class TestAssetCRUD:
    def test_create_asset(self, client, auth_headers):
        response = create_asset(client, auth_headers, value="api.example.com")
        assert response.status_code == 201
        body = response.json()
        assert body["value"] == "api.example.com"
        assert body["status"] == "active"

    def test_create_without_api_key_is_rejected(self, client):
        response = client.post("/assets", json={
            "type": "domain", "value": "noauth.com", "source": "scan",
        })
        assert response.status_code in (401, 422)

    def test_get_asset_by_id(self, client, auth_headers):
        created = create_asset(client, auth_headers, value="get-me.com").json()
        response = client.get(f"/assets/{created['id']}")
        assert response.status_code == 200
        assert response.json()["value"] == "get-me.com"

    def test_get_nonexistent_asset_returns_404(self, client):
        response = client.get("/assets/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_update_asset(self, client, auth_headers):
        created = create_asset(client, auth_headers, value="update-me.com").json()
        response = client.put(
            f"/assets/{created['id']}",
            json={"status": "archived"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "archived"

    def test_delete_asset(self, client, auth_headers):
        created = create_asset(client, auth_headers, value="delete-me.com").json()
        response = client.delete(f"/assets/{created['id']}", headers=auth_headers)
        assert response.status_code == 204
        assert client.get(f"/assets/{created['id']}").status_code == 404


class TestDeduplication:
    def test_reimporting_same_value_does_not_duplicate(self, client, auth_headers):
        create_asset(client, auth_headers, value="dup.example.com", tags=["a"])
        second = create_asset(
            client, auth_headers, value="dup.example.com", tags=["b"]
        )
        assert second.status_code == 201

        listing = client.get("/assets", params={"value": "dup.example.com"})
        results = listing.json()
        assert len(results) == 1
        assert set(results[0]["tags"]) == {"a", "b"}

    def test_resighting_updates_last_seen_and_reactivates(self, client, auth_headers):
        first = create_asset(
            client, auth_headers, value="stale-then-seen.com"
        ).json()

        client.post(f"/assets/{first['id']}/mark-stale", headers=auth_headers)
        stale_check = client.get(f"/assets/{first['id']}")
        assert stale_check.json()["status"] == "stale"

        create_asset(client, auth_headers, value="stale-then-seen.com")
        reactivated = client.get(f"/assets/{first['id']}")
        assert reactivated.json()["status"] == "active"


class TestBulkImport:
    def test_bulk_import_ingests_sample_dataset(self, client, auth_headers):
        dataset = [
            {"id": "a1", "type": "domain", "value": "import-example.com",
             "status": "active", "source": "scan", "tags": ["root"], "metadata": {}},
            {"id": "a2", "type": "subdomain", "value": "import-api.example.com",
             "status": "active", "source": "scan", "tags": ["prod"],
             "metadata": {}, "parent": "a1"},
        ]
        file_bytes = io.BytesIO(json.dumps(dataset).encode())

        response = client.post(
            "/assets/import",
            files={"file": ("dataset.json", file_bytes, "application/json")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 2
        assert body["failed"] == 0

    def test_bulk_import_is_idempotent(self, client, auth_headers):
        dataset = [
            {"id": "a1", "type": "domain", "value": "idempotent.com",
             "status": "active", "source": "scan", "tags": [], "metadata": {}},
        ]

        for _ in range(2):
            file_bytes = io.BytesIO(json.dumps(dataset).encode())
            client.post(
                "/assets/import",
                files={"file": ("dataset.json", file_bytes, "application/json")},
                headers=auth_headers,
            )

        listing = client.get("/assets", params={"value": "idempotent.com"})
        assert len(listing.json()) == 1

    def test_bulk_import_handles_malformed_records_gracefully(
        self, client, auth_headers
    ):
        dataset = [
            {"id": "good1", "type": "domain", "value": "good.com",
             "source": "scan"},
            {"id": "bad1", "type": "not-a-real-type", "value": "bad.com"},
        ]
        file_bytes = io.BytesIO(json.dumps(dataset).encode())

        response = client.post(
            "/assets/import",
            files={"file": ("dataset.json", file_bytes, "application/json")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 1
        assert body["failed"] == 1


class TestFilteringSortingPagination:
    def test_filter_by_type_and_status(self, client, auth_headers):
        create_asset(client, auth_headers, value="d1.com", type="domain")
        create_asset(
            client, auth_headers, value="s1.example.com", type="subdomain"
        )

        response = client.get("/assets", params={"type": "subdomain"})
        results = response.json()
        assert all(r["type"] == "subdomain" for r in results)

    def test_pagination_limits_results(self, client, auth_headers):
        for i in range(5):
            create_asset(client, auth_headers, value=f"page-{i}.com")

        response = client.get("/assets", params={"limit": 2, "skip": 0})
        assert len(response.json()) == 2

    def test_sort_by_value_ascending(self, client, auth_headers):
        create_asset(client, auth_headers, value="zzz-sort.com")
        create_asset(client, auth_headers, value="aaa-sort.com")

        response = client.get(
            "/assets",
            params={"value": "sort", "sort_by": "value", "sort_order": "asc"},
        )
        values = [r["value"] for r in response.json()]
        assert values == sorted(values)


class TestRelationships:
    def test_create_and_fetch_relationship_graph(self, client, auth_headers):
        domain = create_asset(client, auth_headers, value="graph-root.com").json()
        subdomain = create_asset(
            client, auth_headers, value="graph-api.graph-root.com", type="subdomain"
        ).json()

        rel_response = client.post(
            "/relationships",
            json={
                "source_asset_id": subdomain["id"],
                "target_asset_id": domain["id"],
                "relationship_type": "parent",
            },
            headers=auth_headers,
        )
        assert rel_response.status_code == 201

        graph = client.get(f"/assets/{domain['id']}/graph")
        assert graph.status_code == 200
        body = graph.json()
        assert body["asset"]["id"] == domain["id"]
        assert len(body["related"]) == 1
        assert body["related"][0]["asset"]["id"] == subdomain["id"]

    def test_relationship_with_missing_asset_returns_404(self, client, auth_headers):
        domain = create_asset(client, auth_headers, value="lonely.com").json()
        response = client.post(
            "/relationships",
            json={
                "source_asset_id": domain["id"],
                "target_asset_id": "00000000-0000-0000-0000-000000000000",
                "relationship_type": "parent",
            },
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestCertificateLifecycle:
    def test_cert_status_expired(self, client, auth_headers):
        response = client.post(
            "/assets",
            json={
                "type": "certificate",
                "value": "CN=expired.example.com",
                "source": "scan",
                "tags": [],
                "metadata_json": {"issuer": "Let's Encrypt", "expires": "2020-01-01"},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["cert_status"] == "expired"

    def test_cert_status_valid(self, client, auth_headers):
        response = client.post(
            "/assets",
            json={
                "type": "certificate",
                "value": "CN=valid.example.com",
                "source": "scan",
                "tags": [],
                "metadata_json": {"issuer": "Let's Encrypt", "expires": "2099-01-01"},
            },
            headers=auth_headers,
        )
        assert response.json()["cert_status"] == "valid"

    def test_cert_status_none_for_non_certificate_assets(self, client, auth_headers):
        response = create_asset(client, auth_headers, value="not-a-cert.com")
        assert response.json()["cert_status"] is None

    def test_filter_certificates_by_expired_status(self, client, auth_headers):
        client.post(
            "/assets",
            json={
                "type": "certificate", "value": "CN=will-expire.com",
                "source": "scan", "tags": [],
                "metadata_json": {"expires": "2020-06-01"},
            },
            headers=auth_headers,
        )
        client.post(
            "/assets",
            json={
                "type": "certificate", "value": "CN=still-fine.com",
                "source": "scan", "tags": [],
                "metadata_json": {"expires": "2099-06-01"},
            },
            headers=auth_headers,
        )

        response = client.get(
            "/assets/certificates", params={"cert_status": "expired"}
        )
        results = response.json()
        assert all(r["cert_status"] == "expired" for r in results)
        assert any(r["value"] == "CN=will-expire.com" for r in results)
        assert not any(r["value"] == "CN=still-fine.com" for r in results)


class TestConsistentErrorShape:
    def test_not_found_error_has_consistent_shape(self, client):
        response = client.get("/assets/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert "message" in body["error"]

    def test_validation_error_has_consistent_shape(self, client, auth_headers):
        response = client.post(
            "/assets",
            json={"type": "not-a-real-type", "value": "x.com", "source": "scan"},
            headers=auth_headers,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert isinstance(body["error"]["details"], list)

    def test_unauthorized_error_has_consistent_shape(self, client):
        response = client.post(
            "/assets",
            json={"type": "domain", "value": "noauth2.com", "source": "scan"},
        )
        assert response.status_code in (401, 422)
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] in ("UNAUTHORIZED", "VALIDATION_ERROR")
