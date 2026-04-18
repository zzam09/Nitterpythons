# Tweet Tracker API Documentation

## Overview

The Tweet Tracker API provides a complete RESTful interface for managing Twitter/X user tracking and tweet data. The API follows a structured JSON response format and includes comprehensive error handling.

**Base URL**: `http://localhost:5000`  
**Content-Type**: `application/json`  
**CORS**: Enabled for all origins

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Short clear message"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible.

---

# User Management Endpoints

## Create User
**POST** `/api/users`

Creates a new user in the tracking system.

### Request Body
```json
{
  "username": "required string",
  "display_name": "optional string",
  "fetch_interval_mins": "optional number >= 1 (default: 15)"
}
```

### Example Request
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "elonmusk",
    "display_name": "Elon Musk",
    "fetch_interval_mins": 30
  }'
```

### Success Response (201)
```json
{
  "success": true,
  "data": {
    "username": "elonmusk",
    "display_name": "Elon Musk",
    "is_active": 1,
    "fetch_interval_mins": 30,
    "last_fetched": null,
    "created_at": "2026-04-18 11:26:18",
    "added_at": "2026-04-18 11:26:18",
    "tweet_count": 0,
    "retweet_count": 0
  },
  "message": "User @elonmusk added successfully"
}
```

### Error Responses
- `400` - `INVALID_INPUT`: username is required or fetch_interval_mins < 1
- `409` - `DUPLICATE_USER`: User already exists
- `500` - `INTERNAL_ERROR`: Server error

---

## Get All Users
**GET** `/api/users`

Retrieves all tracked users with their statistics.

### Example Request
```bash
curl -X GET http://localhost:5000/api/users
```

### Success Response (200)
```json
{
  "success": true,
  "data": [
    {
      "username": "elonmusk",
      "display_name": "Elon Musk",
      "is_active": 1,
      "last_fetched": "2026-04-18 11:20:00",
      "tweet_count": 150,
      "retweet_count": 25,
      "fetch_interval_mins": 30,
      "added_at": "2026-04-18 11:26:18"
    },
    {
      "username": "nasa",
      "display_name": null,
      "is_active": 1,
      "last_fetched": "2026-04-18 11:25:00",
      "tweet_count": 200,
      "retweet_count": 10,
      "fetch_interval_mins": 15,
      "added_at": "2026-04-18 11:26:18"
    }
  ],
  "message": "Retrieved 2 users"
}
```

### Error Response
- `500` - `INTERNAL_ERROR`: Server error

---

## Get Single User
**GET** `/api/users/{username}`

Retrieves information for a specific user.

### Path Parameters
- `username` (string): The username to retrieve (without @)

### Example Request
```bash
curl -X GET http://localhost:5000/api/users/elonmusk
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "username": "elonmusk",
    "display_name": "Elon Musk",
    "is_active": 1,
    "fetch_interval_mins": 30,
    "last_fetched": "2026-04-18 11:20:00",
    "created_at": "2026-04-18 11:26:18",
    "added_at": "2026-04-18 11:26:18",
    "tweet_count": 150,
    "retweet_count": 25
  },
  "message": "User @elonmusk retrieved successfully"
}
```

### Error Responses
- `404` - `USER_NOT_FOUND`: User does not exist
- `500` - `INTERNAL_ERROR`: Server error

---

## Update User
**PUT** `/api/users/{username}`  
**PATCH** `/api/users/{username}`

Updates an existing user's information. Both methods work identically.

### Path Parameters
- `username` (string): The username to update

### Request Body
```json
{
  "display_name": "optional string",
  "fetch_interval_mins": "optional number >= 1",
  "is_active": "optional boolean"
}
```

### Example Request
```bash
curl -X PATCH http://localhost:5000/api/users/elonmusk \
  -H "Content-Type: application/json" \
  -d '{
    "fetch_interval_mins": 45,
    "display_name": "Updated Name",
    "is_active": false
  }'
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "username": "elonmusk",
    "display_name": "Updated Name",
    "is_active": 0,
    "fetch_interval_mins": 45,
    "last_fetched": "2026-04-18 11:20:00",
    "created_at": "2026-04-18 11:26:18",
    "added_at": "2026-04-18 11:26:18",
    "tweet_count": 150,
    "retweet_count": 25
  },
  "message": "User @elonmusk updated successfully"
}
```

### Error Responses
- `400` - `INVALID_INPUT`: No valid fields to update or invalid values
- `404` - `USER_NOT_FOUND`: User does not exist
- `500` - `INTERNAL_ERROR`: Server error

---

## Delete User
**DELETE** `/api/users/{username}`

Deletes a user from the system. Optionally deletes their tweets.

### Path Parameters
- `username` (string): The username to delete

### Query Parameters
- `delete_tweets` (boolean): `"true"` to delete user's tweets, `"false"` (default) to keep them

### Example Request
```bash
# Delete user but keep tweets
curl -X DELETE http://localhost:5000/api/users/elonmusk

# Delete user and their tweets
curl -X DELETE http://localhost:5000/api/users/elonmusk?delete_tweets=true
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "username": "elonmusk",
    "deleted_tweets": true,
    "tweet_count_deleted": 150,
    "retweet_count_deleted": 25
  },
  "message": "User @elonmusk deleted successfully"
}
```

### Error Responses
- `404` - `USER_NOT_FOUND`: User does not exist
- `500` - `INTERNAL_ERROR`: Server error

---

# Tweet Management Endpoints

## Get All Tweets
**GET** `/api/tweets`

Retrieves all saved tweets from the database.

### Query Parameters
- `username` (string, optional): Filter tweets by specific username

### Example Requests
```bash
# Get all tweets
curl -X GET http://localhost:5000/api/tweets

# Get tweets for specific user
curl -X GET http://localhost:5000/api/tweets?username=elonmusk
```

### Success Response (200)
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "tweet_id": "1234567890",
      "username": "elonmusk",
      "content": "Hello Twitter!",
      "x_url": "https://x.com/elonmusk/status/1234567890",
      "nitter_url": "http://mail.tidebridges.com:8091/elonmusk/status/1234567890",
      "published_at": "Mon, 18 Apr 2026 10:00:00 GMT",
      "is_retweet": 0,
      "saved_at": "2026-04-18 11:26:18"
    }
  ],
  "message": "Retrieved 1 tweets"
}
```

### Error Response
- `500` - `INTERNAL_ERROR`: Server error

---

## Get User Tweets
**GET** `/api/tweets/{username}`

Retrieves all tweets for a specific user.

### Path Parameters
- `username` (string): The username to retrieve tweets for

### Example Request
```bash
curl -X GET http://localhost:5000/api/tweets/elonmusk
```

### Success Response (200)
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "tweet_id": "1234567890",
      "username": "elonmusk",
      "content": "Hello Twitter!",
      "x_url": "https://x.com/elonmusk/status/1234567890",
      "nitter_url": "http://mail.tidebridges.com:8091/elonmusk/status/1234567890",
      "published_at": "Mon, 18 Apr 2026 10:00:00 GMT",
      "is_retweet": 0,
      "saved_at": "2026-04-18 11:26:18"
    }
  ],
  "message": "Retrieved 1 tweets"
}
```

### Error Responses
- `404` - `USER_NOT_FOUND`: User does not exist
- `500` - `INTERNAL_ERROR`: Server error

---

# Statistics Endpoints

## Get System Stats
**GET** `/api/stats`

Retrieves overall system statistics.

### Example Request
```bash
curl -X GET http://localhost:5000/api/stats
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "total_users": 5,
    "total_tweets": 1250,
    "total_retweets": 180,
    "last_updated": "2026-04-18 11:25:00"
  },
  "message": "Stats retrieved successfully"
}
```

### Error Response
- `500` - `INTERNAL_ERROR`: Server error

---

# Configuration Endpoints

## Get Configuration
**GET** `/api/config`

Returns current configuration values (non-sensitive).

### Example Request
```bash
curl -X GET http://localhost:5000/api/config
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "db_path": "tweets.db",
    "turso_url": "(not set)",
    "turso_token_set": false,
    "nitter_base": "http://mail.tidebridges.com:8091",
    "request_timeout_secs": 15,
    "max_retries": 3,
    "retry_delay_secs": 2.0,
    "retry_backoff": 2.0,
    "flask_host": "0.0.0.0",
    "flask_port": 5000,
    "scheduler_sync_secs": 60,
    "default_fetch_interval_mins": 15
  },
  "message": "Configuration retrieved successfully"
}
```

### Error Response
- `500` - `INTERNAL_ERROR`: Server error

---

## Get Settings
**GET** `/api/settings`

Returns all editable settings with their current values and sources.

### Example Request
```bash
curl -X GET http://localhost:5000/api/settings
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "NITTER_BASE": {
      "label": "Nitter Base URL",
      "type": "text",
      "default": "http://mail.tidebridges.com:8091",
      "hint": "Base URL of your Nitter instance",
      "value": "https://nitter.net",
      "source": "file"
    },
    "REQUEST_TIMEOUT": {
      "label": "Request Timeout (seconds)",
      "type": "int",
      "default": 15,
      "hint": "Seconds before a fetch request is aborted",
      "value": 30,
      "source": "file"
    },
    "MAX_RETRIES": {
      "label": "Max Retries",
      "type": "int",
      "default": 3,
      "hint": "How many times to retry a failed fetch",
      "value": 3,
      "source": "default"
    }
  },
  "message": "Settings retrieved successfully"
}
```

**Source Types:**
- `file`: Overridden in settings.json
- `env`: Set via environment variable
- `default`: Using hardcoded default

### Error Response
- `500` - `INTERNAL_ERROR`: Server error

---

## Update Settings
**POST** `/api/settings`

Updates multiple settings and saves them to settings.json.

### Request Body
```json
{
  "NITTER_BASE": "https://nitter.net",
  "REQUEST_TIMEOUT": 30,
  "MAX_RETRIES": 5
}
```

### Example Request
```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "NITTER_BASE": "https://nitter.net",
    "REQUEST_TIMEOUT": 30,
    "MAX_RETRIES": 5
  }'
```

### Success Response (200)
```json
{
  "success": true,
  "data": {
    "NITTER_BASE": {
      "label": "Nitter Base URL",
      "type": "text",
      "default": "http://mail.tidebridges.com:8091",
      "hint": "Base URL of your Nitter instance",
      "value": "https://nitter.net",
      "source": "file"
    },
    "REQUEST_TIMEOUT": {
      "label": "Request Timeout (seconds)",
      "type": "int",
      "default": 15,
      "hint": "Seconds before a fetch request is aborted",
      "value": 30,
      "source": "file"
    },
    "MAX_RETRIES": {
      "label": "Max Retries",
      "type": "int",
      "default": 3,
      "hint": "How many times to retry a failed fetch",
      "value": 5,
      "source": "file"
    }
  },
  "message": "Settings updated successfully"
}
```

### Special Operations

#### Reset All Settings
```json
{"_reset": true}
```

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"_reset": true}'
```

### Error Responses
- `400` - `INVALID_INPUT`: Invalid setting values
- `500` - `INTERNAL_ERROR`: Server error

---

# Web Interface Endpoints

## Dashboard
**GET** `/`

Returns the main dashboard HTML interface with user statistics and navigation.

### Example Request
```bash
curl -X GET http://localhost:5000/
```

### Response
Returns HTML dashboard page.

---

## User Detail Page
**GET** `/user/{username}`

Returns a web page showing all tweets for a specific user.

### Path Parameters
- `username` (string): The username to view

### Example Request
```bash
curl -X GET http://localhost:5000/user/elonmusk
```

### Response
Returns HTML page with user's tweets.

---

## Settings Page
**GET** `/settings`

Returns the settings management HTML interface.

### Example Request
```bash
curl -X GET http://localhost:5000/settings
```

### Response
Returns HTML settings page.

---

## API Documentation
**GET** `/docs`

Returns the API documentation HTML interface.

### Example Request
```bash
curl -X GET http://localhost:5000/docs
```

### Response
Returns HTML documentation page.

---

# Error Codes Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_INPUT` | 400 | Request data is invalid or missing required fields |
| `DUPLICATE_USER` | 409 | User already exists in the database |
| `USER_NOT_FOUND` | 404 | User does not exist in the database |
| `INTERNAL_ERROR` | 500 | Server-side error occurred |

---

# Data Models

## User Model
```json
{
  "username": "string (unique)",
  "display_name": "string (nullable)",
  "is_active": "boolean",
  "fetch_interval_mins": "integer",
  "last_fetched": "datetime (nullable)",
  "created_at": "datetime",
  "added_at": "datetime",
  "tweet_count": "integer",
  "retweet_count": "integer"
}
```

## Tweet Model
```json
{
  "id": "integer",
  "tweet_id": "string (unique)",
  "username": "string",
  "content": "string",
  "x_url": "string",
  "nitter_url": "string (nullable)",
  "published_at": "datetime (string)",
  "is_retweet": "boolean",
  "saved_at": "datetime"
}
```

---

# Configuration Priority

Settings are resolved in the following priority order (highest to lowest):

1. **settings.json** - File-based overrides (highest priority)
2. **Environment Variables** - .env file or system environment
3. **Hardcoded Defaults** - Built-in default values (lowest priority)

---

# Quick Start Examples

## 1. Add a New User
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "nasa", "fetch_interval_mins": 20}'
```

## 2. Get All Users
```bash
curl -X GET http://localhost:5000/api/users
```

## 3. Update User Settings
```bash
curl -X PATCH http://localhost:5000/api/users/nasa \
  -H "Content-Type: application/json" \
  -d '{"fetch_interval_mins": 30, "is_active": false}'
```

## 4. Get User's Tweets
```bash
curl -X GET http://localhost:5000/api/tweets/nasa
```

## 5. Update System Settings
```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"REQUEST_TIMEOUT": 25, "MAX_RETRIES": 5}'
```

## 6. Delete User
```bash
curl -X DELETE http://localhost:5000/api/users/nasa?delete_tweets=true
```

---

# Rate Limits & Performance

- No rate limiting currently implemented
- All requests are processed synchronously
- Database operations use connection pooling
- Large datasets may require pagination (not yet implemented)

---

# Support

For issues or questions:
1. Check the server logs for detailed error messages
2. Verify all required fields are provided
3. Ensure proper JSON formatting in request bodies
4. Use the `/docs` endpoint for interactive API testing
