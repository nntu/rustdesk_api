# RustDesk Web API Client Documentation

This document outlines the Web API endpoints used by the RustDesk client, based on the codebase analysis.

## Base URL
The base URL is generally configured via the `api-server` option.

## Endpoints

### 1. Login Options
Used to detect TLS support and configure the HTTP client.

- **URL:** `/api/login-options`
- **Method:** `POST`
- **Description:**  The client initializes its HTTP client using this URL. It is primarily used to detect the appropriate TLS implementation for the server and potentially fallback options.

### 2. OIDC Authentication
Handles OpenID Connect authentication.

#### Initiate Auth
- **URL:** `/api/oidc/auth`
- **Method:** `POST`
- **Payload (JSON):**
    ```json
    {
      "op": "string",
      "id": "string",
      "uuid": "string",
      "deviceInfo": {
        "os": "string",
        "type": "string",
        "name": "string"
      }
    }
    ```

#### Query Auth Status
- **URL:** `/api/oidc/auth-query`
- **Method:** `GET`
- **Query Parameters:**
    - `code`: The authorization code received from the initiate step.
    - `id`: Client ID.
    - `uuid`: Client UUID.

### 3. Heartbeat & Synchronization
Maintains connection status and synchronizes configuration.

#### Heartbeat
- **URL:** `/api/heartbeat`
- **Method:** `POST`
- **Payload (JSON):**
    ```json
    {
      "id": "string",
      "uuid": "string",
      "ver": number,
      "conns": [number], // Optional: List of active connection IDs
      "modified_at": number // Timestamp of last strategy update
    }
    ```
- **Response (JSON):**
    - `sysinfo`: If present, triggers a system info upload.
    - `disconnect`: List of connection IDs to force disconnect.
    - `modified_at`: Timestamp for strategy updates.
    - `strategy`: Object containing configuration strategies.

#### Upload System Info
- **URL:** `/api/sysinfo`
- **Method:** `POST`
- **Description:** Uploads client system information to the server. Triggered if the heartbeat response requests it.
- **Payload (JSON):**
    ```json
    {
      "version": "string",
      "id": "string",
      "uuid": "string",
      "username": "string",
      "hostname": "string",
      // ... plus various preset options if configured
    }
    ```

#### Check System Info Version
- **URL:** `/api/sysinfo_ver`
- **Method:** `POST`
- **Description:** Verifies the version of the system info on the server.
- **Payload:** (Empty body)

### 4. Record Upload
Uploads session recordings to the server.

- **URL:** `/api/record`
- **Method:** `POST`
- **Query Parameters:**
    - `type`: Action type (`new`, `part`, `tail`, `remove`).
    - `file`: The filename of the recording.
    - `offset`: (Required for `part` and `tail`) Byte offset.
    - `length`: (Required for `part` and `tail`) Length of the chunk.
- **Body:** Binary content of the recording chunk.

### 5. File Download
General file download utility.

- **URL:** (Dynamic)
- **Method:** `HEAD` (to check size), `GET` (to download)

### 6. Audit Logs
Used to log various events to the server.

#### Connection Audit
- **URL:** `/api/audit/conn`
- **Method:** `POST`
- **Payload (JSON):**
    ```json
    {
      "id": "string",
      "uuid": "string",
      "conn_id": number,
      "session_id": number,
      "peer": ["peer_id", "peer_name"],
      "type": number // Connection type
    }
    ```

#### File Transfer Audit
- **URL:** `/api/audit/file`
- **Method:** `POST`
- **Payload (JSON):**
    ```json
    {
      "id": "string",
      "uuid": "string",
      "peer_id": "string",
      "type": number,
      "path": "string",
      "is_file": boolean,
      "info": "string" // JSON string containing file details, ip, name
    }
    ```

#### Alarm Audit
- **URL:** `/api/audit/alarm`
- **Method:** `POST`
- **Payload (JSON):**
    ```json
    {
      "id": "string",
      "uuid": "string",
      "typ": number,
      "info": "string" // JSON string with additional info
    }
    ```

### 7. Software Update
Checks for the latest version of the client.

- **URL:** `https://api.rustdesk.com/version/latest` (Default, can be overridden)
- **Method:** `POST`
- **Payload:** JSON object with version check request details.
- **Response (JSON):**
    ```json
    {
      "url": "string" // URL to the new version
    }
    ```
