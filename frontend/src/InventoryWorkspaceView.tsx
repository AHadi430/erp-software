import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Product, request } from "./api";
import { InventoryView } from "./OperationsViews";
import { ProductAutocomplete } from "./ProductAutocomplete";

type ProductPlus = Product & { sku?: string };
export function InventoryWorkspaceView() {
  const client = useQueryClient(); const [productId, setProductId] = useState(""); const [quantity, setQuantity] = useState(""); const [notes, setNotes] = useState("");
  const products = useQuery({ queryKey: ["products"], queryFn: () => request<ProductPlus[]>("/products?limit=200") });
  const adjustment = useMutation({ mutationFn: () => request("/inventory/adjustments", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: Number(quantity), notes }) }), onSuccess: () => { setProductId(""); setQuantity(""); setNotes(""); client.invalidateQueries({ queryKey: ["stock"] }); client.invalidateQueries({ queryKey: ["stock-movements"] }); client.invalidateQueries({ queryKey: ["dashboard"] }); } });
  const selected = products.data?.find(p => p.id === productId);
  return <><section className="panel quick-inventory"><p className="eyebrow">QUICK STOCK</p><h2>Fast stock adjustment</h2><div className="line-adder"><ProductAutocomplete products={products.data ?? []} value={productId} onChange={setProductId} placeholder="Type shade, paint name or SKU…" /><input type="number" step="0.001" placeholder="+/- quantity" value={quantity} onChange={e => setQuantity(e.target.value)} /><input placeholder="Reason / notes" value={notes} onChange={e => setNotes(e.target.value)} /><button type="button" disabled={!productId || !quantity || adjustment.isPending} onClick={() => adjustment.mutate()}>{adjustment.isPending ? "Posting…" : "Post adjustment"}</button></div>{selected && <p className="hint">Selected: <strong>{selected.name}</strong> · {selected.packaging}</p>}{adjustment.error && <p className="error">{adjustment.error.message}</p>}{adjustment.isSuccess && <p className="success">Stock adjustment posted.</p>}</section><InventoryView /></>;
}
