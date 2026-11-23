Authentication

GET /api/auth/csrf
POST /api/auth/login
GET /api/auth/session

Subscriber Management

GET /api/db/subscriber
GET /api/db/subscriber/{imsi}

Authentication Flow

1. Obtain CSRF token
2. Login with admin/1423
3. Retrieve JWT from /api/auth/session
4. Use Authorization: Bearer <JWT> for /api/db/* endpoints

Verified using Python client.
