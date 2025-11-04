import { useState } from "react";
import { useWidgetState } from "../use-widget-state";
import "./auth-screen.css";

/**
 * Authentication screen for AllôBye
 * Provides login, signup, and password reset flows
 */
export default function AuthScreen({ onAuthenticated }) {
  const [state, setState] = useWidgetState({
    mode: "login", // 'login' | 'signup' | 'reset'
    loading: false,
    error: null,
  });

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
    role: "parent",
    confirmPassword: "",
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setState({ ...state, loading: true, error: null });

    try {
      if (!window.openai?.callTool) {
        throw new Error("MCP tools not available");
      }

      const result = await window.openai.callTool("auth-login", {
        email: formData.email,
        password: formData.password,
      });

      // Store session in localStorage
      if (result?.structuredContent?.access_token) {
        localStorage.setItem("allobye_token", result.structuredContent.access_token);
        localStorage.setItem("allobye_user", JSON.stringify(result._meta?.profile || {}));

        // Notify parent component
        if (onAuthenticated) {
          onAuthenticated({
            token: result.structuredContent.access_token,
            user: result._meta?.profile,
          });
        }

        setState({ ...state, loading: false });
      } else {
        throw new Error("Login failed: No access token returned");
      }
    } catch (error) {
      console.error("Login error:", error);
      setState({
        ...state,
        loading: false,
        error: error.message || "Email ou mot de passe incorrect",
      });
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setState({ ...state, error: "Les mots de passe ne correspondent pas" });
      return;
    }

    if (formData.password.length < 6) {
      setState({ ...state, error: "Le mot de passe doit contenir au moins 6 caractères" });
      return;
    }

    setState({ ...state, loading: true, error: null });

    try {
      if (!window.openai?.callTool) {
        throw new Error("MCP tools not available");
      }

      const result = await window.openai.callTool("auth-signup", {
        email: formData.email,
        password: formData.password,
        name: formData.name,
        role: formData.role,
      });

      // Auto-login after signup if session is available
      if (result?._meta?.session?.access_token) {
        localStorage.setItem("allobye_token", result._meta.session.access_token);

        // Get full profile
        const profileResult = await window.openai.callTool("auth-profile", {
          accessToken: result._meta.session.access_token,
        });

        if (profileResult?.structuredContent) {
          localStorage.setItem("allobye_user", JSON.stringify(profileResult.structuredContent));

          if (onAuthenticated) {
            onAuthenticated({
              token: result._meta.session.access_token,
              user: profileResult.structuredContent,
            });
          }
        }
      } else {
        // Show success message and switch to login
        setState({
          ...state,
          loading: false,
          mode: "login",
          error: null,
        });
        alert("Compte créé avec succès! Veuillez vérifier votre email et vous connecter.");
      }
    } catch (error) {
      console.error("Signup error:", error);
      setState({
        ...state,
        loading: false,
        error: error.message || "Erreur lors de la création du compte",
      });
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setState({ ...state, loading: true, error: null });

    try {
      if (!window.openai?.callTool) {
        throw new Error("MCP tools not available");
      }

      await window.openai.callTool("auth-reset-password", {
        email: formData.email,
      });

      alert("Email de réinitialisation envoyé! Veuillez vérifier votre boîte de réception.");
      setState({ ...state, loading: false, mode: "login" });
    } catch (error) {
      console.error("Reset password error:", error);
      setState({
        ...state,
        loading: false,
        error: "Erreur lors de l'envoi de l'email de réinitialisation",
      });
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-container">
        <div className="auth-header">
          <h1>AllôBye</h1>
          <p className="auth-subtitle">Gestion des ramassages scolaires</p>
        </div>

        {state.error && (
          <div className="auth-error">
            <span className="error-icon">⚠️</span>
            {state.error}
          </div>
        )}

        {state.mode === "login" && (
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Connexion</h2>

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                autoComplete="email"
                placeholder="votre@email.com"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Mot de passe</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                autoComplete="current-password"
                placeholder="••••••••"
              />
            </div>

            <button type="submit" className="btn-primary" disabled={state.loading}>
              {state.loading ? "Connexion..." : "Se connecter"}
            </button>

            <div className="auth-links">
              <button
                type="button"
                className="link-button"
                onClick={() => setState({ ...state, mode: "reset", error: null })}
              >
                Mot de passe oublié?
              </button>
              <button
                type="button"
                className="link-button"
                onClick={() => setState({ ...state, mode: "signup", error: null })}
              >
                Créer un compte
              </button>
            </div>
          </form>
        )}

        {state.mode === "signup" && (
          <form onSubmit={handleSignup} className="auth-form">
            <h2>Inscription</h2>

            <div className="form-group">
              <label htmlFor="name">Nom complet</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Jean Tremblay"
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                autoComplete="email"
                placeholder="votre@email.com"
              />
            </div>

            <div className="form-group">
              <label htmlFor="role">Rôle</label>
              <select id="role" name="role" value={formData.role} onChange={handleInputChange}>
                <option value="parent">Parent</option>
                <option value="school_staff">Personnel scolaire</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="password">Mot de passe</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                autoComplete="new-password"
                placeholder="••••••••"
                minLength={6}
              />
              <small>Minimum 6 caractères</small>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirmer le mot de passe</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                required
                autoComplete="new-password"
                placeholder="••••••••"
              />
            </div>

            <button type="submit" className="btn-primary" disabled={state.loading}>
              {state.loading ? "Création..." : "Créer mon compte"}
            </button>

            <div className="auth-links">
              <button
                type="button"
                className="link-button"
                onClick={() => setState({ ...state, mode: "login", error: null })}
              >
                Déjà un compte? Se connecter
              </button>
            </div>
          </form>
        )}

        {state.mode === "reset" && (
          <form onSubmit={handleResetPassword} className="auth-form">
            <h2>Réinitialiser le mot de passe</h2>
            <p className="reset-description">
              Entrez votre email et nous vous enverrons un lien pour réinitialiser votre mot de passe.
            </p>

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                autoComplete="email"
                placeholder="votre@email.com"
              />
            </div>

            <button type="submit" className="btn-primary" disabled={state.loading}>
              {state.loading ? "Envoi..." : "Envoyer le lien"}
            </button>

            <div className="auth-links">
              <button
                type="button"
                className="link-button"
                onClick={() => setState({ ...state, mode: "login", error: null })}
              >
                Retour à la connexion
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
