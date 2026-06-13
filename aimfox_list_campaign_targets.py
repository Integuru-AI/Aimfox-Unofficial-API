from curl_cffi import requests


def run(headers, user_input):
    """List all targets in a specific Aimfox campaign with their outreach status."""
    base_url = BASE_URL

    # Validate input
    workspace_id = user_input.get("workspace_id")
    if not workspace_id:
        return {'status_code': 400, 'body': {'error': 'workspace_id is required'}}

    campaign_id = user_input.get("campaign_id")
    if not campaign_id:
        return {'status_code': 400, 'body': {'error': 'campaign_id is required'}}

    # Fetch campaign audience
    response = _call_api(base_url, workspace_id, campaign_id, headers)

    # Check for auth failure
    if response.status_code == 401:
        return {'status_code': 401, 'body': {'error': 'Unauthorized - session expired'}}

    # Cloudflare or permission block
    if response.status_code == 403:
        return {'status_code': 403, 'body': {'error': 'Access denied', 'detail': response.text[:200]}}

    # Some platforms redirect to login on expired sessions
    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("Location", "")
        if "login" in location or "auth" in location or "realms" in location:
            return {'status_code': 401, 'body': {'error': 'Session expired - redirected to login'}}

    if response.status_code != 200:
        return {'status_code': response.status_code, 'body': {'error': f'API returned {response.status_code}', 'detail': response.text[:200]}}

    data = response.json()

    if data.get("status") != "ok":
        return {'status_code': 500, 'body': {'error': 'Unexpected response status', 'detail': data.get("status")}}

    # Map API states to user-friendly status labels
    state_map = {
        "init": "pending",
        "view": "pending",
        "connect": "invited",
        "message": "connected",
        "done": "replied",
        "withdraw": "invited",
        "cancelled": "cancelled",
    }

    # Build clean target list
    targets = []
    for entry in data.get("audience", []):
        targets.append({
            "id": entry.get("id"),
            "full_name": entry.get("full_name"),
            "linkedin_url": f"https://www.linkedin.com/in/{entry.get('public_identifier', '')}",
            "company": entry.get("company"),
            "state": state_map.get(entry.get("state", ""), entry.get("state", "")),
            "raw_state": entry.get("state"),
            "occupation": entry.get("occupation"),
            "location": entry.get("location", {}).get("name") if isinstance(entry.get("location"), dict) else None,
        })

    return {
        'status_code': 200,
        'body': {
            'total': len(targets),
            'targets': targets,
        }
    }


# === PRIVATE ===

def _call_api(base_url, workspace_id, campaign_id, headers):
    """Fetch campaign audience from Aimfox API."""
    return requests.get(
        f"{base_url}/api/v1/workspaces/{workspace_id}/campaigns/{campaign_id}/audience",
        headers={
            "Authorization": headers.get("Authorization", ""),
        },
        impersonate="chrome131",
        timeout=60,
    )
