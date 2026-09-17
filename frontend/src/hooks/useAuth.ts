import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCurrentUser,
  loginUser,
  registerUser,
  type LoginPayload,
  type RegisterPayload,
} from "../api/auth";
import { useAuthStore } from "../store/authStore";

export function useCurrentUser() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const user = await fetchCurrentUser();
      setUser(user);
      return user;
    },
    enabled: Boolean(accessToken),
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: LoginPayload) => loginUser(payload),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => registerUser(payload),
  });
}

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();

  return () => {
    logout();
    queryClient.clear();
  };
}
