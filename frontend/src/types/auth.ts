export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  is_admin: boolean;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  created_at: string;
  last_login: string;
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
