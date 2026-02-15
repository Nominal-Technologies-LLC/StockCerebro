export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
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
