import { api } from "@/lib/api";
import type { Order, OrderCreate, OrdersQuery, OrderUpdate } from "@/types";

export const ordersService = {
  list: (query: OrdersQuery = {}) => api.get<Order[]>("/orders", query),
  get: (id: string) => api.get<Order>(`/orders/${id}`),
  create: (body: OrderCreate) => api.post<Order>("/orders", body),
  update: (id: string, body: OrderUpdate) => api.put<Order>(`/orders/${id}`, body),
  cancel: (id: string) => api.post<Order>(`/orders/${id}/cancel`),
};
