import { createRoot } from "react-dom/client";
import { useState, useEffect, useCallback, useMemo } from "react";
import Dashboard from "./dashboard";
import AuthScreen from "./auth-screen";

/**
 * Main app wrapper with authentication
 */
function App() {
  const [authState, setAuthState] = useState({
    isAuthenticated: false,
    token: null,
    user: null,
    loading: true,
  });

  const validateToken = useCallback(async (token) => {
    if (!window.openai?.callTool) return;

    try {
      const result = await window.openai.callTool("auth-profile", {
        accessToken: token,
      });

      if (result?.structuredContent) {
        // Update user data
        localStorage.setItem("allobye_user", JSON.stringify(result.structuredContent));
        setAuthState((prev) => ({
          ...prev,
          user: result.structuredContent,
        }));
      }
    } catch (error) {
      console.error("Token validation failed:", error);
      throw error;
    }
  }, []);

  const handleLogout = useCallback(async () => {
    const token = authState.token;

    // Call logout on server
    if (token && window.openai?.callTool) {
      try {
        await window.openai.callTool("auth-logout", {
          accessToken: token,
        });
      } catch (error) {
        console.error("Logout error:", error);
      }
    }

    // Clear local session
    localStorage.removeItem("allobye_token");
    localStorage.removeItem("allobye_user");

    setAuthState({
      isAuthenticated: false,
      token: null,
      user: null,
      loading: false,
    });
  }, [authState.token]);

  // Check for existing session on mount
  useEffect(() => {
    const token = localStorage.getItem("allobye_token");
    const userStr = localStorage.getItem("allobye_user");

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        setAuthState({
          isAuthenticated: true,
          token,
          user,
          loading: false,
        });

        // Optionally validate token with server
        validateToken(token).catch(() => {
          // Token invalid, clear and show login
          handleLogout();
        });
      } catch (error) {
        console.error("Error restoring session:", error);
        setAuthState({ isAuthenticated: false, token: null, user: null, loading: false });
      }
    } else {
      setAuthState({ isAuthenticated: false, token: null, user: null, loading: false });
    }
  }, [validateToken, handleLogout]);

  const handleAuthenticated = useCallback(({ token, user }) => {
    setAuthState({
      isAuthenticated: true,
      token,
      user,
      loading: false,
    });
  }, []);

  const loadingStyle = useMemo(() => ({
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    fontFamily: "sans-serif",
    color: "#667eea"
  }), []);

  if (authState.loading) {
    return (
      <div style={loadingStyle}>
        <div>Chargement...</div>
      </div>
    );
  }

  if (!authState.isAuthenticated) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  return <Dashboard user={authState.user} token={authState.token} onLogout={handleLogout} />;
}

createRoot(document.getElementById("allobye-dashboard-root")).render(<App />);
