# RustDesk Web API Implementation Guide

This document provides a practical guide for implementing a client or server module that interacts with the RustDesk Web API. It is based on the analysis of the official RustDesk client codebase.

## 1. Prerequisites & Configuration

Before implementing the API logic, ensure you have the following configuration available:
*   **`api-server`**: The base URL of the API server (e.g., `https://admin.rustdesk.com` or your self-hosted URL).
*   **`id`**: The unique ID of the RustDesk client.
*   **`uuid`**: The persistent unique identifier of the installation.

## 2. Authentication Flow (OIDC)

### Overview
The OIDC authentication flow involves an initial request to start the process, followed by polling for the status until a token is received or a timeout occurs.

### Implementation Logic

1.  **Start Authentication**:
    *   Call `POST /api/oidc/auth` with `op`, `id`, `uuid`, and `deviceInfo`.
    *   **Response**: Receives a JSON object containing `code` and `url`.
    *   **Action**: Open `url` in the user's browser so they can log in.

2.  **Poll for Token**:
    *   Start a loop that runs every **1 second**.
    *   **Timeout**: Default is 180 seconds (3 minutes).
    *   **Loop**:
        *   Call `GET /api/oidc/auth-query` with query params: `code` (from step 1), `id`, `uuid`.
        *   **Success**: If the response contains an `access_token`, save it and the user info. Break the loop.
        *   **Error**: If the error is "No authed oidc is found", continue polling. Other errors might stop the loop depending on severity.

## 3. Heartbeat & Synchronization Loop

This is the core background process that keeps the client connected to the web console.

### Loop Specification
*   **Interval**: 3 seconds (`TIME_CONN`).
*   **Heartbeat Throttle**: Only send the actual heartbeat request every 15 seconds (`TIME_HEARTBEAT`) *unless* there are active connections (`conns` is not empty), in which case it may send more frequently (every 3s).

### Step-by-Step Logic (Pseudo-code)

```python
last_sent = 0
info_uploaded = { uploaded: false, url: "", id: "", ... }

while True:
    sleep(3) # Tick every 3 seconds
    
    url = get_heartbeat_url()
    if not url: continue
    
    # 1. Check/Upload System Info
    # If URL or ID changed, or if sysinfo hasn't been uploaded for 120s
    if needs_sysinfo_upload(info_uploaded):
        sysinfo = gather_system_info() # CPU, Ram, OS, User, etc.
        sysinfo_payload = {
            ...sysinfo,
            "id": config.id,
            "uuid": config.uuid,
            "version": client_version,
            # ... preset options like address book name, tags, etc.
        }
        
        # Optimization: Check hash if public server
        if is_public_server(url):
             current_hash = calculate_hash(sysinfo_payload)
             if current_hash == stored_hash:
                  if check_server_version(url) == local_version:
                       continue_to_next_step()
        
        response = POST(url.replace("heartbeat", "sysinfo"), sysinfo_payload)
        if response == "SYSINFO_UPDATED":
             mark_uploaded(info_uploaded)
             
    # 2. Send Heartbeat
    active_conns = get_active_connection_ids()
    if empty(active_conns) and (now() - last_sent < 15s):
        continue # Skip if no active connections and not enough time passed

    payload = {
        "id": config.id,
        "uuid": config.uuid,
        "ver": client_version,
        "modified_at": last_strategy_timestamp, # Timestamp of last received strategy
    }
    if active_conns:
        payload["conns"] = active_conns

    response = POST(url, payload)
    last_sent = now()

    # 3. Handle Response
    if response contains "sysinfo":
        info_uploaded.uploaded = False # Force re-upload next tick
    
    if response contains "disconnect":
        force_disconnect_connections(response["disconnect"])
        
    if response contains "strategy":
        update_local_strategies(response["strategy"])
        
    if response contains "modified_at":
        update_last_strategy_timestamp(response["modified_at"])
```

## 4. Audit Logging

Audit logs should be sent asynchronously to avoid blocking the main thread.

### Connection Audit
*   **Trigger**: When a session connects (authenticated).
*   **Endpoint**: `/api/audit/conn`
*   **Payload**:
    *   `conn_id`: The ID of the connection.
    *   `session_id`: The session ID.
    *   `type`: Connection type (0=Remote, 1=FileTransfer, 2=PortForward, etc.).
    *   `peer`: Tuple of `[peer_id, peer_name]`.

### File Transfer Audit
*   **Trigger**: When a file transfer job completes or a batch of files is processed.
*   **Endpoint**: `/api/audit/file`
*   **Payload**:
    *   `type`: Job type.
    *   `path`: Remote path.
    *   `is_file`: Boolean.
    *   `info`: JSON string containing list of files (`name`, `size`).

## 5. Record Uploading

Recordings are uploaded in chunks.

### Logic
1.  **New File**: When a recording starts.
    *   `POST /api/record?type=new&file=<filename>`
2.  **Part Upload**: While recording, as the file grows.
    *   Check if file grew by at least 1MB (`SHOULD_SEND_SIZE`) or 1 second passed (`SHOULD_SEND_TIME`).
    *   Read new bytes.
    *   `POST /api/record?type=part&file=<filename>&offset=<offset>&length=<len>` (Body is raw bytes).
3.  **Tail/Finish**: When recording stops.
    *   Flush remaining bytes.
    *   `POST /api/record?type=tail&...`
4.  **Remove**: If the file is deleted locally (optional logic).
    *   `POST /api/record?type=remove&...`
