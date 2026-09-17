import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../api/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  activeProfileId: string | null;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: User) => void;
  setActiveProfileId: (profileId: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      activeProfileId: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setUser: (user) => set({ user }),
      setActiveProfileId: (activeProfileId) => set({ activeProfileId }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, user: null, activeProfileId: null }),
    }),
    { name: "remoteradar-auth" },
  ),
);
