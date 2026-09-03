import { useMemo, useState } from "react";
import { Product } from "./api";

type ProductOption = Product & { sku?: string };

type Props = {
  products: ProductOption[];
  value: string;
  onChange: (productId: string) => void;
  placeholder?: string;
};

export function ProductAutocomplete({ products, value, onChange, placeholder = "Type shade, paint name or SKU…" }: Props) {
  const selected = products.find(product => product.id === value);
  const [search, setSearch] = useState(selected ? `${selected.sku ?? ""} — ${selected.name} (${selected.packaging})` : "");

  const matches = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return products.slice(0, 12);
    return products.filter(product => `${product.sku ?? ""} ${product.name} ${product.packaging}`.toLowerCase().includes(query)).slice(0, 12);
  }, [products, search]);

  const choose = (product: ProductOption) => {
    onChange(product.id);
    setSearch(`${product.sku ?? ""} — ${product.name} (${product.packaging})`);
  };

  return <div className="autocomplete-wrap">
    <input
      required
      aria-label="Product"
      placeholder={placeholder}
      value={search}
      onChange={event => {
        setSearch(event.target.value);
        onChange("");
      }}
      onFocus={() => { if (selected) setSearch(""); }}
      autoComplete="off"
    />
    {search && !selected && <div className="autocomplete-list">
      {matches.map(product => <button type="button" key={product.id} onMouseDown={event => event.preventDefault()} onClick={() => choose(product)}>
        <strong>{product.name}</strong>
        <small>{product.sku ?? ""} · {product.packaging}</small>
      </button>)}
      {!matches.length && <p>No matching paint found.</p>}
    </div>}
  </div>;
}
