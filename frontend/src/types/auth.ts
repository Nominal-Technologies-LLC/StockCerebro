export interface SubscriptionInfo {
  status: 'admin' | 'override' | 'paid' | 'trialing' | 'expired';
  has_access: boolean;
  has_macro_access: boolean;
  trial_ends_at: string | null;
}

export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  is_admin: boolean;
  subscription: SubscriptionInfo | null;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  created_at: string;
  last_login: string;
  subscription_status: string | null;
  subscription_override: boolean;
  trial_ends_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}
