const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export type User = { id: string; email: string; full_name: string; role: string; is_active: boolean };
export type Category = { id: string; name: string; description?: string; is_active: boolean };
export type Product = { id: string; sku: string; name: string; selling_price: string; cost_price: string; is_active: boolean };
export type Party = { id: string; name: string; is_active: boolean };
export type InvoiceLine = { product_id: string; quantity: number; unit_price: number; discount_amount: number };
export type InvoiceResult = { invoice_number: string; grand_total: string; due_amount: string };

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers }
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(detail.detail ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}
