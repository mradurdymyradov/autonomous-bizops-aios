# Instagram Publishing API — @voronka.tm

Reference for the Meta Graph API configuration used by the local poster automation.

## Core Metadata
- **Instagram User ID (Account)**: `17841480213410482`
- **Linked Facebook Page**: `voronka.tm` (ID `1180291058506773`)
- **Meta App**: `automation_1` (App ID `4473106283009964`)
- **Graph Version**: `v21.0` (endpoint prefix: `https://graph.facebook.com/v21.0`)
- **Auth**: Permanent Page access token stored in `IG_ACCESS_TOKEN` in `ig-poster/.env`.

---

## Image Hosting: imgbb API
Because the Instagram Graph API requires a public URL to fetch media from, we upload local images to imgbb first.
- **Endpoint**: `POST https://api.imgbb.com/1/upload`
- **Params**: `key={IMGBB_API_KEY}`
- **Files**: `image={file_handle}`
- **Response JSON Path**: `data.url` (gives the public direct image URL).

---

## Publishing Workflow

### 1. Feed / Story Single Container Creation
- **Endpoint**: `POST /{IG_USER_ID}/media`
- **Data (Payload)**:
  - `image_url`: Publicly accessible image URL (e.g., from imgbb)
  - `access_token`: Page access token
  - `caption`: (Optional, omitted for stories) Caption text
  - `media_type`: Set to `STORIES` for stories, omit for standard feed photo.
- **Response**: `{ "id": "<CONTAINER_ID>" }`

### 2. Carousel Container Creation (Multi-image)
First, create an individual container for each image:
- **Endpoint**: `POST /{IG_USER_ID}/media`
- **Data**:
  - `image_url`: Publicly accessible image URL
  - `is_carousel_item`: `true`
  - `access_token`: Page access token
- **Response**: `{ "id": "<CHILD_CONTAINER_ID>" }`

Then, create the main carousel container linking the children:
- **Endpoint**: `POST /{IG_USER_ID}/media`
- **Data**:
  - `media_type`: `CAROUSEL`
  - `children`: Comma-separated list of child IDs (e.g., `cid1,cid2,cid3`)
  - `caption`: (Optional) Caption text
  - `access_token`: Page access token
- **Response**: `{ "id": "<CAROUSEL_CONTAINER_ID>" }`

### 3. Check Container Status
Wait for Meta to process the image container before publishing.
- **Endpoint**: `GET /{container_id}`
- **Params**: `fields=status_code`, `access_token={token}`
- **Response Status Codes**:
  - `FINISHED`: Container is ready to publish.
  - `IN_PROGRESS`: Wait and poll again.
  - `ERROR`: Processing failed.

### 4. Publish Container
- **Endpoint**: `POST /{IG_USER_ID}/media_publish`
- **Data**:
  - `creation_id`: `<CONTAINER_ID>` or `<CAROUSEL_CONTAINER_ID>`
  - `access_token`: Page access token
- **Response**: `{ "id": "<PUBLISHED_MEDIA_ID>" }`

---

## Deletion Workflow (Not Currently Enabled)

Meta provides an endpoint to delete published Instagram media (non-ad posts, Stories, and Reels).

### 1. Requirements & Permissions
- **Required Permissions**: `instagram_basic` AND `instagram_manage_contents` (our current token lacks `instagram_manage_contents`).
- **Token**: A Page Access Token generated via Facebook Login for Business.
- **Enablement**: Operator would need to regenerate the access token through the Meta developer portal/Graph API Explorer, adding the `instagram_manage_contents` permission.

### 2. Deletion Endpoint
- **Endpoint**: `DELETE /{ig-media-id}`
- **Params**: `access_token={token}`
- **Response**: `{ "success": true }`

### 3. Limitations & Known Issues
- **Carousel Albums**: You cannot delete individual media items inside a carousel; you must delete the entire carousel container by its media ID.
- **API Instability**: The endpoint is notoriously unstable on Meta's backend. Developers frequently report "fatal internal server errors" (subcode `2207085`) even with correct permissions.

---

## Retries & Network Notes
The connection runs over a slow and flaky VPN (2-4 Mb/s) which drops frequently. All Graph API and imgbb calls must run with automated retry-and-backoff logic (implemented in `post.py`).

