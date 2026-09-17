import { apiFetch } from "@/lib/api";
import type { AuthUser } from "@/store/auth-store";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function registerUser(payload: { email: string; password: string }): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/register", { method: "POST", body: payload, skipAuth: true });
}

export function loginUser(payload: { email: string; password: string }): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/login", { method: "POST", body: payload, skipAuth: true });
}

export function fetchCurrentUser(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/me");
}
