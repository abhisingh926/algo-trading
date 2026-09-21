import { api } from "@/lib/api";
import type { AuthStatus, AuthToken, LoginRequest, RegisterRequest, User } from "@/types";

export const authService = {
  status: () => api.get<AuthStatus>("/auth/status"),
  register: (body: RegisterRequest) => api.post<AuthToken>("/auth/register", body),
  login: (body: LoginRequest) => api.post<AuthToken>("/auth/login", body),
  me: () => api.get<User>("/auth/me"),
};
