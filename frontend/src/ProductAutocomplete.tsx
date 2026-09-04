import { useMemo, useState } from "react";
import { Product } from "./api";

type ProductOption = Product & { sku?: string };

type Props = {
  products: ProductOption[];
  value: string;
  onChange: (productId: string) => void;
  placeholder?: string;
};

export function ProductAutocomplete({
  products,
  value,
  onChange,
  placeholder = "Type shade, paint name or SKU…",
}: Props) {
  const selected = products.find((product) => product.id === value);

  const [search, setSearch] = useState("");
  const [focused, setFocused] = useState(false);

  const matches = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return products.slice(0, 12);
    }

    return products
      .filter((product) => {
        const name = String(product.name ?? "").toLowerCase();
        const sku = String(product.sku ?? "").toLowerCase();
        const packaging = String(product.packaging ?? "").toLowerCase();
        const shade = String((product as ProductOption & { shade?: string }).shade ?? "").toLowerCase();

        return (
          name.includes(query) ||
          sku.includes(query) ||
          packaging.includes(query) ||
          shade.includes(query)
        );
      })
      .slice(0, 12);
  }, [products, search]);

  const choose = (product: ProductOption) => {
    onChange(product.id);

    setSearch(
      `${product.sku ?? ""} — ${product.name} (${product.packaging})`
    );

    setFocused(false);
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const text = event.target.value;

    setSearch(text);
    setFocused(true);

    // Important: typing means we are searching for a new product.
    onChange("");
  };

  return (
    <div className="autocomplete-wrap">
      <input
        required
        aria-label="Product"
        placeholder={placeholder}
        value={
          selected && !focused
            ? `${selected.sku ?? ""} — ${selected.name} (${selected.packaging})`
            : search
        }
        onFocus={() => {
          setFocused(true);

          // Allow the user to immediately type a new search.
          if (selected) {
            setSearch("");
          }
        }}
        onChange={handleChange}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setFocused(false);
            return;
          }

          if (event.key === "Enter" && matches.length === 1) {
            event.preventDefault();
            choose(matches[0]);
          }
        }}
        onBlur={() => {
          window.setTimeout(() => setFocused(false), 150);
        }}
        autoComplete="off"
      />

      {focused && (
        <div className="autocomplete-list">
          {matches.map((product) => (
            <button
              type="button"
              key={product.id}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(product)}
            >
              <strong>{product.name}</strong>

              <small>
                {product.sku ?? ""}
                {product.sku ? " · " : ""}
                {product.packaging}
              </small>
            </button>
          ))}

          {!matches.length && (
            <p>No matching paint found.</p>
          )}
        </div>
      )}
    </div>
  );
}