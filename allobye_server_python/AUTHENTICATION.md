# AllôBye Authentication System

## Overview

The AllôBye MCP server integrates Supabase email/password authentication with role-based access control (RBAC) to protect pickup management tools and school dashboards.

## Architecture

### Components

1. **Authentication Module** (`auth.py`)
   - User signup and login with Supabase Auth
   - Password reset functionality
   - Email verification support
   - JWT token validation
   - User profile management

2. **MCP Authentication Tools** (in `main.py`)
   - `auth-signup`: Register new users
   - `auth-login`: Login with credentials
   - `auth-logout`: Logout and invalidate session
   - `auth-reset-password`: Request password reset
   - `auth-profile`: Get current user profile

3. **React Authentication Screen** (`src/allobye-dashboard/auth-screen.jsx`)
   - Login form
   - Signup form
   - Password reset form
   - Session persistence in localStorage
   - Auto-redirect on authentication

## User Roles

### Parent
- Can schedule pickups for their children
- Can authorize delegates for their children
- Can declare emergencies for their children
- Access controlled by parent-child relationships

### School Staff
- Can view school dashboard
- Can see pickup queue for their schools
- Access controlled by staff-school relationships

## Authentication Flow

### 1. Signup Flow

```
User -> auth-signup MCP tool
  ↓
Supabase Auth creates user
  ↓
User profile created in database
  ↓
Email verification sent (optional)
  ↓
Session token returned
```

**MCP Tool Call:**
```json
{
  "tool": "auth-signup",
  "arguments": {
    "email": "parent@example.com",
    "password": "secure123",
    "name": "Jean Tremblay",
    "role": "parent"
  }
}
```

**Response:**
```json
{
  "user_id": "uuid-here",
  "email": "parent@example.com",
  "email_verified": false,
  "session": {
    "access_token": "jwt-token-here",
    "refresh_token": "refresh-token-here",
    "expires_at": "2025-11-05T12:00:00Z"
  }
}
```

### 2. Login Flow

```
User -> auth-login MCP tool
  ↓
Credentials validated by Supabase
  ↓
User profile fetched from database
  ↓
Session token + profile returned
```

**MCP Tool Call:**
```json
{
  "tool": "auth-login",
  "arguments": {
    "email": "parent@example.com",
    "password": "secure123"
  }
}
```

**Response:**
```json
{
  "user_id": "uuid-here",
  "email": "parent@example.com",
  "role": "parent",
  "access_token": "jwt-token-here",
  "profile": {
    "id": "uuid-here",
    "email": "parent@example.com",
    "name": "Jean Tremblay",
    "role": "parent",
    "children": ["child-id-1", "child-id-2"],
    "schools": []
  }
}
```

### 3. Authenticated Tool Calls

All protected tools require the `accessToken` parameter:

```json
{
  "tool": "pickup-schedule-create",
  "arguments": {
    "accessToken": "jwt-token-here",
    "childIds": ["child-id-1"],
    "pickupPersonId": "delegate-id",
    "scheduledTime": "2025-11-04T15:30:00-05:00"
  }
}
```

The server:
1. Extracts the `accessToken` from arguments
2. Validates the JWT with Supabase
3. Loads the user profile
4. Checks role permissions
5. Verifies resource ownership (e.g., parent owns child)
6. Executes the tool if authorized

### 4. Session Management

**Client-side (React):**
- Access token stored in `localStorage` as `allobye_token`
- User profile stored in `localStorage` as `allobye_user`
- Token validated on app mount
- Auto-logout if token expired

**Server-side:**
- JWT tokens validated with Supabase Auth
- Token expiration checked automatically
- Refresh tokens can be used to renew sessions

## Database Schema

### user_profiles

Stores user metadata and role information.

```sql
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT NOT NULL,
  name TEXT,
  role TEXT NOT NULL CHECK (role IN ('parent', 'school_staff')),
  email_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### user_schools

Links school staff to their schools.

```sql
CREATE TABLE user_schools (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES user_profiles(id),
  school_id UUID REFERENCES schools(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, school_id)
);
```

### parent_children

Links parents to their children.

```sql
CREATE TABLE parent_children (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parent_id UUID REFERENCES user_profiles(id),
  child_id UUID REFERENCES children(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(parent_id, child_id)
);
```

## Authorization Rules

### pickup-schedule-create
- **Required Role:** `parent`
- **Resource Check:** Parent must own all children in `childIds`

### delegate-authorize
- **Required Role:** `parent`
- **Resource Check:** Parent must own all children in `childIds`

### emergency-declare
- **Required Role:** `parent`
- **Resource Check:** Parent must own the child in `childId`

### school-dashboard-fetch
- **Required Role:** `school_staff`
- **Resource Check:** Staff must be associated with the school in `schoolId`

## Security Considerations

### Password Requirements
- Minimum 6 characters (enforced by Supabase)
- Can be strengthened in Supabase Auth settings

### JWT Tokens
- Signed by Supabase with HS256
- Include user ID and email in payload
- Expire after configurable duration (default: 1 hour)
- Refresh tokens allow session renewal

### Environment Variables

Required in `.env`:

```bash
# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Important:**
- `ANON_KEY` is used for client-side auth operations (signup, login)
- `SERVICE_ROLE_KEY` is used for server-side privileged operations
- Never expose `SERVICE_ROLE_KEY` to the client

### CORS Configuration

The server allows all origins for development:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)
```

**Production:** Restrict `allow_origins` to your domain.

## Error Handling

### Authentication Errors

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `InvalidCredentialsError` | 401 | Invalid email/password |
| `EmailNotVerifiedError` | 403 | Email not verified |
| `UserAlreadyExistsError` | 409 | User already exists |
| `SessionExpiredError` | 401 | JWT token expired |
| `AuthenticationError` | 400/500 | General auth error |

### Example Error Response

```json
{
  "content": [
    {
      "type": "text",
      "text": "Session expirée. Veuillez vous reconnecter."
    }
  ],
  "isError": true
}
```

## Testing Authentication

### 1. Create Test User

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "auth-signup",
      "arguments": {
        "email": "test@example.com",
        "password": "test123",
        "name": "Test User",
        "role": "parent"
      }
    }
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "auth-login",
      "arguments": {
        "email": "test@example.com",
        "password": "test123"
      }
    }
  }'
```

### 3. Use Authenticated Tool

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "auth-profile",
      "arguments": {
        "accessToken": "YOUR_JWT_TOKEN_HERE"
      }
    }
  }'
```

## React Integration

### App Wrapper

The main app (`src/allobye-dashboard/index.jsx`) wraps the dashboard with authentication:

```jsx
function App() {
  const [authState, setAuthState] = useState({
    isAuthenticated: false,
    token: null,
    user: null,
    loading: true,
  });

  // Check for existing session on mount
  useEffect(() => {
    const token = localStorage.getItem("allobye_token");
    const userStr = localStorage.getItem("allobye_user");

    if (token && userStr) {
      setAuthState({
        isAuthenticated: true,
        token,
        user: JSON.parse(userStr),
        loading: false,
      });
    }
  }, []);

  if (!authState.isAuthenticated) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  return <Dashboard user={authState.user} token={authState.token} />;
}
```

### Making Authenticated Calls

```jsx
// In React component
const schedulePickup = async (childIds, pickupPersonId, scheduledTime) => {
  const token = localStorage.getItem("allobye_token");

  const result = await window.openai.callTool("pickup-schedule-create", {
    accessToken: token,
    childIds,
    pickupPersonId,
    scheduledTime,
  });

  return result;
};
```

## Migration Notes

### Existing Users

If you have existing users in the database without Supabase Auth accounts:

1. Users must sign up again with their email
2. Link their Supabase user ID to existing profile
3. Or create a migration script to create Supabase accounts

### Mock Mode

For development without Supabase:

- Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` to empty in `.env`
- Server will fall back to mock authentication
- All authentication will succeed with mock data
- **Not suitable for production**

## Troubleshooting

### Token Validation Fails

**Problem:** "Session expired" errors

**Solutions:**
- Check token hasn't actually expired
- Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Check Supabase project is active
- Ensure token is being passed correctly in `accessToken` field

### Cannot Access Tool

**Problem:** "Authentification requise" errors

**Solutions:**
- Verify user is logged in
- Check `accessToken` is included in tool arguments
- Verify user has the correct role for the tool
- Check resource ownership (e.g., parent owns child)

### Signup Fails

**Problem:** User signup returns error

**Solutions:**
- Check password meets minimum requirements (6+ chars)
- Verify email is valid format
- Check if user already exists
- Review Supabase Auth logs for detailed error

## Future Enhancements

- [ ] Two-factor authentication (2FA)
- [ ] Social login (Google, Apple)
- [ ] Password complexity requirements
- [ ] Rate limiting on auth endpoints
- [ ] Audit logging for auth events
- [ ] Role-based permissions matrix
- [ ] Admin role for user management
- [ ] Email verification enforcement
- [ ] Session timeout configuration
- [ ] Remember me functionality

## Related Files

- `/home/user/openai-apps-sdk-examples/allobye_server_python/auth.py` - Authentication module
- `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py` - MCP server with auth tools
- `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/auth-screen.jsx` - React auth component
- `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/index.jsx` - App wrapper with auth
- `/home/user/openai-apps-sdk-examples/allobye_server_python/.env` - Environment configuration
