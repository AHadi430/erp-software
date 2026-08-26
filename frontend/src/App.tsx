import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Category, login, request, User } from "./api";
import { InvoiceEntry } from "./InvoiceEntry";
import { DashboardView, InventoryView, SettingsView } from "./OperationsViews";

function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const mutation = useMutation({ mutationFn: () => login(email, password), onSuccess: ({ access_token }) => { localStorage.setItem("access_token", access_token); onLogin(); } });
  const submit = (event: FormEvent) => { event.preventDefault(); mutation.mutate(); };
  return <main className="login"><form onSubmit={submit}><h1>Paint Shop ERP</h1><p>Sign in to manage your business.</p><label>Email<input type="email" required value={email} onChange={e => setEmail(e.target.value)} /></label><label>Password<input type="password" required value={password} onChange={e => setPassword(e.target.value)} /></label>{mutation.error && <p className="error">{mutation.error.message}</p>}<button disabled={mutation.isPending}>{mutation.isPending ? "Signing in…" : "Sign in"}</button></form></main>;
}

function Dashboard({ user }: { user: User }) {
  const queryClient = useQueryClient(); const [name, setName] = useState("");
  const [screen, setScreen] = useState<"dashboard" | "sales" | "purchases" | "inventory" | "settings">("dashboard");
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => request<Category[]>("/categories") });
  const addCategory = useMutation({ mutationFn: () => request<Category>("/categories", { method: "POST", body: JSON.stringify({ name }) }), onSuccess: () => { setName(""); queryClient.invalidateQueries({ queryKey: ["categories"] }); } });
  const dashboard = <><DashboardView /><section className="panel"><h2>Product categories</h2><p>Create the paint categories you sell.</p><form className="inline" onSubmit={e => { e.preventDefault(); if (name.trim()) addCategory.mutate(); }}><input aria-label="Category name" placeholder="e.g. Interior Emulsion" value={name} onChange={e => setName(e.target.value)} /><button disabled={addCategory.isPending}>Add category</button></form>{addCategory.error && <p className="error">{addCategory.error.message}</p>}{categories.isPending ? <p>Loading categories…</p> : <ul>{categories.data?.map(category => <li key={category.id}>{category.name}</li>)}</ul>}</section></>;
  const content = screen === "sales" ? <InvoiceEntry kind="sale" /> : screen === "purchases" ? <InvoiceEntry kind="purchase" /> : screen === "inventory" ? <InventoryView /> : screen === "settings" ? <SettingsView /> : dashboard;
  return <div className="layout"><aside><h2>Paint Shop</h2><nav>{(["dashboard", "sales", "purchases", "inventory", "settings"] as const).map(item => <button key={item} className={screen === item ? "active" : ""} onClick={() => setScreen(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</nav></aside><main className="content"><header><div><p className="eyebrow">WELCOME BACK</p><h1>{user.full_name}</h1></div><button className="secondary" onClick={() => { localStorage.removeItem("access_token"); location.reload(); }}>Sign out</button></header>{content}</main></div>;
}

export function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(localStorage.getItem("access_token")));
  const me = useQuery({ queryKey: ["me"], queryFn: () => request<User>("/auth/me"), enabled: authenticated, retry: false });
  if (!authenticated) return <Login onLogin={() => setAuthenticated(true)} />;
  if (me.isPending) return <main className="login">Loading your workspace…</main>;
  if (me.error || !me.data) { localStorage.removeItem("access_token"); return <Login onLogin={() => setAuthenticated(true)} />; }
  return <Dashboard user={me.data} />;
}
