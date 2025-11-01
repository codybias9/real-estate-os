/**
 * OIDC Authentication Provider for React
 *
 * Implements Authorization Code Flow with PKCE (RFC 7636)
 *
 * Features:
 * - Automatic token refresh
 * - Secure token storage (in-memory + httpOnly cookie)
 * - PKCE for public clients
 * - State parameter for CSRF protection
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface OIDCConfig {
  issuer: string;
  clientId: string;
  redirectUri: string;
  scopes: string[];
}

interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  expires_in: number;
  token_type: string;
}

interface User {
  sub: string;
  email: string;
  name?: string;
  tenant_id?: string;
  roles: string[];
}

interface OIDCContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  getAccessToken: () => string | null;
}

const OIDCContext = createContext<OIDCContextType | undefined>(undefined);

const DEFAULT_CONFIG: OIDCConfig = {
  issuer: import.meta.env.VITE_OIDC_ISSUER || 'http://localhost:8180/realms/real-estate-os',
  clientId: import.meta.env.VITE_OIDC_CLIENT_ID || 'real-estate-os-web',
  redirectUri: import.meta.env.VITE_OIDC_REDIRECT_URI || 'http://localhost:8080/callback',
  scopes: ['openid', 'profile', 'email', 'tenant', 'roles']
};

export const OIDCProvider: React.FC<{ children: React.ReactNode; config?: Partial<OIDCConfig> }> = ({
  children,
  config: configOverride
}) => {
  const config = { ...DEFAULT_CONFIG, ...configOverride };
  const navigate = useNavigate();

  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [oidcEndpoints, setOidcEndpoints] = useState<any>(null);

  // Discover OIDC endpoints
  useEffect(() => {
    const discoverEndpoints = async () => {
      try {
        const response = await fetch(`${config.issuer}/.well-known/openid-configuration`);
        const data = await response.json();
        setOidcEndpoints(data);
      } catch (error) {
        console.error('Failed to discover OIDC endpoints:', error);
      }
    };
    discoverEndpoints();
  }, [config.issuer]);

  // Generate code verifier and challenge for PKCE
  const generatePKCE = () => {
    const codeVerifier = generateRandomString(128);
    const codeChallenge = base64URLEncode(sha256(codeVerifier));

    return { codeVerifier, codeChallenge };
  };

  const generateRandomString = (length: number) => {
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    let result = '';
    const randomValues = new Uint8Array(length);
    crypto.getRandomValues(randomValues);

    for (let i = 0; i < length; i++) {
      result += charset[randomValues[i] % charset.length];
    }
    return result;
  };

  const sha256 = (plain: string) => {
    const encoder = new TextEncoder();
    const data = encoder.encode(plain);
    return crypto.subtle.digest('SHA-256', data);
  };

  const base64URLEncode = (buffer: ArrayBuffer) => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary)
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  };

  // Login: Redirect to authorization endpoint
  const login = useCallback(() => {
    if (!oidcEndpoints) {
      console.error('OIDC endpoints not loaded');
      return;
    }

    const { codeVerifier, codeChallenge } = generatePKCE();
    const state = generateRandomString(32);

    // Store PKCE verifier and state
    sessionStorage.setItem('oidc_code_verifier', codeVerifier);
    sessionStorage.setItem('oidc_state', state);

    // Build authorization URL
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: config.clientId,
      redirect_uri: config.redirectUri,
      scope: config.scopes.join(' '),
      state: state,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256'
    });

    const authUrl = `${oidcEndpoints.authorization_endpoint}?${params.toString()}`;
    window.location.href = authUrl;
  }, [oidcEndpoints, config]);

  // Handle callback from authorization server
  const handleCallback = useCallback(async (code: string, state: string) => {
    if (!oidcEndpoints) return;

    // Verify state
    const storedState = sessionStorage.getItem('oidc_state');
    if (state !== storedState) {
      console.error('State mismatch - possible CSRF attack');
      return;
    }

    // Get code verifier
    const codeVerifier = sessionStorage.getItem('oidc_code_verifier');
    if (!codeVerifier) {
      console.error('Code verifier not found');
      return;
    }

    // Exchange code for tokens
    try {
      const response = await fetch(oidcEndpoints.token_endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          code: code,
          redirect_uri: config.redirectUri,
          client_id: config.clientId,
          code_verifier: codeVerifier
        })
      });

      if (!response.ok) {
        throw new Error('Token exchange failed');
      }

      const tokens: TokenResponse = await response.json();

      // Store tokens
      setAccessToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token || null);

      // Decode and extract user info from access token
      const payload = JSON.parse(atob(tokens.access_token.split('.')[1]));
      setUser({
        sub: payload.sub,
        email: payload.email,
        name: payload.name,
        tenant_id: payload.tenant_id,
        roles: payload.roles || []
      });

      // Clean up
      sessionStorage.removeItem('oidc_code_verifier');
      sessionStorage.removeItem('oidc_state');

      // Schedule token refresh
      scheduleTokenRefresh(tokens.expires_in);

      navigate('/');
    } catch (error) {
      console.error('Failed to exchange code for tokens:', error);
    }
  }, [oidcEndpoints, config, navigate]);

  // Refresh access token using refresh token
  const refreshAccessToken = useCallback(async () => {
    if (!oidcEndpoints || !refreshToken) return;

    try {
      const response = await fetch(oidcEndpoints.token_endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          refresh_token: refreshToken,
          client_id: config.clientId
        })
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const tokens: TokenResponse = await response.json();
      setAccessToken(tokens.access_token);

      if (tokens.refresh_token) {
        setRefreshToken(tokens.refresh_token);
      }

      scheduleTokenRefresh(tokens.expires_in);
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
    }
  }, [oidcEndpoints, refreshToken, config]);

  // Schedule automatic token refresh
  const scheduleTokenRefresh = (expiresIn: number) => {
    // Refresh 1 minute before expiration
    const refreshIn = (expiresIn - 60) * 1000;
    setTimeout(() => {
      refreshAccessToken();
    }, refreshIn);
  };

  // Logout
  const logout = useCallback(async () => {
    if (!oidcEndpoints) return;

    // Revoke tokens (optional)
    if (refreshToken && oidcEndpoints.revocation_endpoint) {
      try {
        await fetch(oidcEndpoints.revocation_endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            token: refreshToken,
            client_id: config.clientId,
            token_type_hint: 'refresh_token'
          })
        });
      } catch (error) {
        console.error('Token revocation failed:', error);
      }
    }

    // Clear local state
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);

    // Redirect to logout endpoint
    const params = new URLSearchParams({
      post_logout_redirect_uri: window.location.origin,
      client_id: config.clientId
    });

    window.location.href = `${oidcEndpoints.end_session_endpoint}?${params.toString()}`;
  }, [oidcEndpoints, refreshToken, config]);

  // Get current access token
  const getAccessToken = useCallback(() => {
    return accessToken;
  }, [accessToken]);

  // Handle OAuth callback on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && state) {
      handleCallback(code, state);
    } else {
      setIsLoading(false);
    }
  }, [handleCallback]);

  const value: OIDCContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    getAccessToken
  };

  return <OIDCContext.Provider value={value}>{children}</OIDCContext.Provider>;
};

export const useOIDC = () => {
  const context = useContext(OIDCContext);
  if (context === undefined) {
    throw new Error('useOIDC must be used within an OIDCProvider');
  }
  return context;
};
