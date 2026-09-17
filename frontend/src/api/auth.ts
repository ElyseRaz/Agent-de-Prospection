import { apiFetch } from "./client";
import type { AccessToken, TokenPair, User } from "./types";

export interface RegisterPayload {
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  totp_code?: string;
}

export function registerUser(payload: RegisterPayload): Promise<User> {
  return apiFetch<User>("/auth/register", { method: "POST", body: payload, skipAuth: true });
}

export function loginUser(payload: LoginPayload): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/login", { method: "POST", body: payload, skipAuth: true });
}

export function refreshToken(refresh_token: string): Promise<AccessToken> {
  return apiFetch<AccessToken>("/auth/refresh", {
    method: "POST",
    body: { refresh_token },
    skipAuth: true,
  });
}

export function fetchCurrentUser(): Promise<User> {
  return apiFetch<User>("/auth/me");
}
