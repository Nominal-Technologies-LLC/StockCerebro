import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, SubscriptionInfo } from '../types/auth';
import { getCurrentUser, logout as apiLogout, fetchSubscriptionStatus } from '../api/client';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  subscription: SubscriptionInfo | null;
  hasAccess: boolean;
  hasMacroAccess: boolean;
  login: (user: User) => void;
  logout: () => Promise<void>;
  refreshSubscription: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);

  const refreshSubscription = useCallback(async () => {
    try {
      const status = await fetchSubscriptionStatus();
      setSubscription(status);
    } catch {
      // If fetch fails, fall back to user's embedded subscription info
    }
  }, []);

  useEffect(() => {
    getCurrentUser()
      .then((userData) => {
        setUser(userData);
        setSubscription(userData.subscription ?? null);
      })
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = (userData: User) => {
    setUser(userData);
    setSubscription(userData.subscription ?? null);
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
    setSubscription(null);
  };

  const hasAccess = !!(
    user?.is_admin ||
    subscription?.has_access
  );

  const hasMacroAccess = !!(
    user?.is_admin ||
    subscription?.has_macro_access
  );

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthenticated: !!user,
      subscription,
      hasAccess,
      hasMacroAccess,
      login,
      logout,
      refreshSubscription,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
