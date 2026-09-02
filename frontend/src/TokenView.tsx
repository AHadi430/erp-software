import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "./api";

type TokenInventory = { received: string; issued: string; sales_return: string; purchase_return: string; claimed: string; available: string; shortage?: string };
type Claim = { id: string; claim_number: string; claim_date: string; painter_name: string; painter_phone?: string; quantity: string; token_value: string; total_amount: string; status: string; payment_method?: string };
type TokenProduct = { id: string; sku: string; name: string; packaging: string; token_enabled: boolean; token_value: string };

const whole = (v: string | number | undefined) => Math.max(0, Math.trunc(Number(v ?? 0)));
const pkr = (v: string | number) => new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v));

export function TokenView() {
  const client = useQueryClient();
  const [tab, setTab] = useState<"inventory" | "claims">("inventory");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [quantity, setQuantity] = useState("");
  const [value, setValue] = useState("");
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);

  const inventory = useQuery({ queryKey: ["token-inventory"], queryFn: () => request<TokenInventory>("/tokens/inventory") });
  const products = useQuery({ queryKey: ["token-products"], queryFn: () => request<TokenProduct[]>("/products?limit=200") });
  const claims = useQuery({ queryKey: ["token-claims"], queryFn: () => request<Claim[]>("/tokens/claims") });

  const create = useMutation({
    mutationFn: () => request<Claim>("/tokens/claims", { method: "POST", body: JSON.stringify({ painter_name: name, painter_phone: phone || null, quantity: Number(quantity), token_value: Number(value) }) }),
    onSuccess: claim => {
      setName(""); setPhone(""); setQuantity(""); setValue(""); setSelectedClaim(claim);
      client.invalidateQueries({ queryKey: ["token-inventory"] });
      client.invalidateQueries({ queryKey: ["token-claims"] });
    },
  });

  const pay = useMutation({
    mutationFn: ({ id, method }: { id: string; method: string }) => request<Claim>(`/tokens/claims/${id}/pay?method=${method}`, { method: "POST" }),
    onSuccess: claim => {
      setSelectedClaim(claim);
      client.invalidateQueries({ queryKey: ["token-inventory"] });
      client.invalidateQueries({ queryKey: ["token-claims"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const configure = useMutation({
    mutationFn: ({ id, enabled, tokenValue }: { id: string; enabled: boolean; tokenValue: number }) => request(`/tokens/products/${id}`, { method: "PUT", body: JSON.stringify({ token_enabled: enabled, token_value: tokenValue }) }),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["token-products"] }); client.invalidateQueries({ queryKey: ["products"] }); },
  });

  const available = whole(inventory.data?.available);
  const shortage = whole(inventory.data?.shortage);
  const selectedTotal = useMemo(() => selectedClaim ? Number(selectedClaim.total_amount) : 0, [selectedClaim]);
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };

  return <section className="invoice-page">
    <p className="eyebrow">TOKENS</p>
    <h1>Painter token management</h1>
    <p className="hint">Token inventory is driven by posted purchases, sales, returns and painter claims. Token quantities are always whole numbers.</p>
    <div className="tabs">
      <button type="button" className={tab === "inventory" ? "active" : "secondary"} onClick={() => setTab("inventory")}>Token Inventory</button>
      <button type="button" className={tab === "claims" ? "active" : "secondary"} onClick={() => setTab("claims")}>Claims & Reimbursement</button>
    </div>

    {tab === "inventory" ? <>
      <section className="cards">
        <article><span>Received from purchases</span><strong>{whole(inventory.data?.received)}</strong></article>
        <article><span>Used in sales</span><strong>{whole(inventory.data?.issued)}</strong></article>
        <article><span>Sales returns</span><strong>{whole(inventory.data?.sales_return)}</strong></article>
        <article><span>Purchase returns</span><strong>{whole(inventory.data?.purchase_return)}</strong></article>
        <article><span>Claimed by painters</span><strong>{whole(inventory.data?.claimed)}</strong></article>
        <article><span>Available tokens</span><strong>{available}</strong></article>
      </section>
      {shortage > 0 && <section className="panel"><p className="error">Token inventory needs reconciliation: transactions currently show {shortage} more tokens used than received. This is displayed as 0 available rather than a negative balance. Check the affected purchase/sale token flags before accepting a painter claim.</p></section>}
      <section className="panel">
        <h2>Token-bearing packaging configuration</h2>
        <p className="hint">This only provides the default/reference value. A token still has to be manually confirmed on the actual invoice line.</p>
        <table><thead><tr><th>Paint</th><th>Packaging</th><th>Has token</th><th>Token value</th></tr></thead><tbody>{products.data?.map(product => <tr key={product.id}>
          <td>{product.name} <small>{product.sku}</small></td><td>{product.packaging}</td>
          <td><input type="checkbox" checked={product.token_enabled} onChange={e => configure.mutate({ id: product.id, enabled: e.target.checked, tokenValue: Number(product.token_value) })} /></td>
          <td><input type="number" min="0" step="0.01" value={product.token_value} onChange={e => configure.mutate({ id: product.id, enabled: product.token_enabled, tokenValue: Number(e.target.value) })} /></td>
        </tr>)}</tbody></table>
      </section>
      <section className="panel"><h2>Token flow</h2><ul><li>Posted purchase line manually marked as token-bearing → tokens received.</li><li>Posted sale line manually marked as token-bearing → tokens used.</li><li>Sales return → tokens restored.</li><li>Purchase return → tokens removed.</li><li>Painter claim → tokens removed and reimbursement recorded.</li></ul></section>
    </> : <>
      <section className="panel">
        <h2>Record painter claim</h2>
        <p className="hint">Available now: <strong>{available} whole tokens</strong>. The claim reserves those physical tokens. Payment is recorded separately when you pay the painter.</p>
        <form className="settings-form" onSubmit={submit}>
          <input required placeholder="Painter name" value={name} onChange={e => setName(e.target.value)} />
          <input placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} />
          <input required min="1" step="1" inputMode="numeric" type="number" placeholder="Number of tokens (whole number)" value={quantity} onChange={e => setQuantity(e.target.value)} />
          <input required min="0.01" step="0.01" type="number" placeholder="Value per token (PKR)" value={value} onChange={e => setValue(e.target.value)} />
          <button disabled={create.isPending || available < 1}>Create claim invoice</button>
        </form>
        {create.error && <p className="error">{create.error.message}</p>}
      </section>

      {selectedClaim && <section className="panel">
        <div className="invoice-total"><div><p className="eyebrow">TOKEN CLAIM INVOICE</p><h2>{selectedClaim.claim_number}</h2></div><button type="button" className="secondary" onClick={() => window.print()}>Print</button></div>
        <div className="invoice-grid">
          <div><span className="hint">Painter</span><strong>{selectedClaim.painter_name}</strong>{selectedClaim.painter_phone && <small>{selectedClaim.painter_phone}</small>}</div>
          <div><span className="hint">Claim date</span><strong>{selectedClaim.claim_date}</strong></div>
          <div><span className="hint">Tokens received</span><strong>{whole(selectedClaim.quantity)}</strong></div>
          <div><span className="hint">Value per token</span><strong>{pkr(selectedClaim.token_value)}</strong></div>
        </div>
        <div className="invoice-total"><span>Total reimbursement</span><strong>{pkr(selectedTotal)}</strong></div>
        <p className="hint">Status: <strong>{selectedClaim.status.toUpperCase()}</strong>{selectedClaim.payment_method ? ` · Paid via ${selectedClaim.payment_method}` : ""}</p>
        {selectedClaim.status === "pending" && <div><button type="button" onClick={() => pay.mutate({ id: selectedClaim.id, method: "cash" })}>Pay cash — {pkr(selectedClaim.total_amount)}</button><button type="button" className="secondary" onClick={() => pay.mutate({ id: selectedClaim.id, method: "bank_transfer" })}>Pay bank — {pkr(selectedClaim.total_amount)}</button></div>}
        {pay.error && <p className="error">{pay.error.message}</p>}
      </section>}

      <section className="panel">
        <h2>Claim invoices</h2>
        <table><thead><tr><th>Date</th><th>Invoice</th><th>Painter</th><th>Tokens</th><th>Value/token</th><th>Amount</th><th>Status</th><th /></tr></thead><tbody>{claims.data?.map(claim => <tr key={claim.id}>
          <td>{claim.claim_date}</td><td>{claim.claim_number}</td><td>{claim.painter_name}</td><td>{whole(claim.quantity)}</td><td>{pkr(claim.token_value)}</td><td>{pkr(claim.total_amount)}</td><td>{claim.status}</td><td><button type="button" className="text-button" onClick={() => setSelectedClaim(claim)}>View invoice</button></td>
        </tr>)}</tbody></table>
        {!claims.isPending && !claims.data?.length && <p className="empty">No token claim invoices yet.</p>}
      </section>
    </>}
  </section>;
}
