import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Product, request } from "./api";
import { InventoryView } from "./OperationsViews";

type ProductPlus = Product & { sku?: string };
export function InventoryWorkspaceView() {
  const client = useQueryClient(); const [search, setSearch] = useState(""); const [productId, setProductId] = useState(""); const [quantity, setQuantity] = useState(""); const [notes, setNotes] = useState("");
  const products = useQuery({ queryKey: ["products"], queryFn: () => request<ProductPlus[]>("/products?limit=200") });
  const matches = (products.data ?? []).filter(p => `${p.sku ?? ""} ${p.name} ${p.packaging}`.toLowerCase().includes(search.toLowerCase())).slice(0, 12);
  const adjustment = useMutation({ mutationFn: () => request("/inventory/adjustments", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: Number(quantity), notes }) }), onSuccess: () => { setSearch(""); setProductId(""); setQuantity(""); setNotes(""); client.invalidateQueries({ queryKey: ["stock"] }); client.invalidateQueries({ queryKey: ["stock-movements"] }); client.invalidateQueries({ queryKey: ["dashboard"] }); } });
  const selected = products.data?.find(p => p.id === productId);
  return <><section className="panel quick-inventory"><p className="eyebrow">QUICK STOCK</p><h2>Fast stock adjustment</h2><div className="line-adder"><input autoFocus placeholder="Type shade, paint name or SKU…" value={search} onChange={e => { setSearch(e.target.value); setProductId(""); }} />{search && !productId && <div className="autocomplete-list">{matches.map(product => <button type="button" key={product.id} onClick={() => { setProductId(product.id); setSearch(`${product.sku ?? ""} — ${product.name} (${product.packaging})`); }}><strong>{product.name}</strong><small>{product.sku} · {product.packaging}</small></button>)}{!matches.length && <p>No matching paint found.</p>}</div>}<input type="number" step="0.001" placeholder="+/- quantity" value={quantity} onChange={e => setQuantity(e.target.value)} /><input placeholder="Reason / notes" value={notes} onChange={e => setNotes(e.target.value)} /><button type="button" disabled={!productId || !quantity || adjustment.isPending} onClick={() => adjustment.mutate()}>{adjustment.isPending ? "Posting…" : "Post adjustment"}</button></div>{selected && <p className="hint">Selected: <strong>{selected.name}</strong> · {selected.packaging}</p>}{adjustment.error && <p className="error">{adjustment.error.message}</p>}{adjustment.isSuccess && <p className="success">Stock adjustment posted.</p>}</section><InventoryView /></>;
}
