from curl_cffi import requests
import time


def run(headers, user_input):
    """List LinkedIn inbox conversations from Aimfox with last message, participant info, and direction."""
    base_url = BASE_URL

    workspace_id = user_input.get("workspace_id")
    if not workspace_id:
        return {"status_code": 400, "body": {"error": "workspace_id is required"}}

    account_id = user_input.get("account_id")
    count = user_input.get("count", 35)
    before = user_input.get("before")

    # Build query params
    params = {"count": count}
    if before:
        params["before"] = before
    else:
        # Default to current time in milliseconds
        params["before"] = int(time.time() * 1000)

    if account_id:
        params["account_id"] = account_id

    url = f"{base_url}/api/v1/workspaces/{workspace_id}/conversations"

    request_headers = {
        **headers,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://app.aimfox.com/",
        "Origin": "https://app.aimfox.com",
    }

    response = requests.get(
        url,
        params=params,
        headers=request_headers,
        impersonate="chrome120",
        timeout=30,
    )

    if response.status_code == 401 or response.status_code == 403:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {
            "status_code": response.status_code,
            "body": {"error": f"API returned {response.status_code}", "detail": response.text[:500]},
        }

    data = response.json()

    if data.get("status") != "ok":
        return {"status_code": 500, "body": {"error": "Unexpected response", "detail": data}}

    # Transform conversations into user-friendly format
    conversations = []
    for conv in data.get("conversations", []):
        last_msg = conv.get("last_message", {})
        participants = conv.get("participants", [])
        owner = str(conv.get("owner", ""))

        # The participant is the other person (not the account owner)
        participant = participants[0] if participants else {}

        # Determine direction: if sender id matches owner account, it's "sent"
        sender_id = str(last_msg.get("sender", {}).get("id", ""))
        direction = "sent" if sender_id == owner else "received"

        # Build LinkedIn URL from public_identifier
        public_id = participant.get("public_identifier", "")
        linkedin_url = f"https://www.linkedin.com/in/{public_id}" if public_id else None

        # Convert timestamp to ISO format
        created_at_ms = last_msg.get("created_at")
        timestamp_iso = None
        if created_at_ms:
            from datetime import datetime, timezone
            timestamp_iso = datetime.fromtimestamp(created_at_ms / 1000, tz=timezone.utc).isoformat()

        conversations.append({
            "conversation_urn": conv.get("conversation_urn"),
            "participant_full_name": participant.get("full_name"),
            "participant_linkedin_url": linkedin_url,
            "participant_occupation": participant.get("occupation"),
            "last_message_body": last_msg.get("body"),
            "last_message_direction": direction,
            "last_message_sender_name": last_msg.get("sender", {}).get("full_name"),
            "last_message_timestamp": timestamp_iso,
            "unread_count": conv.get("unread_count", 0),
            "connected": conv.get("connected", False),
            "source": conv.get("source"),
            "owner_account_id": owner,
        })

    return {
        "status_code": 200,
        "body": {
            "conversations": conversations,
            "count": len(conversations),
        },
    }
