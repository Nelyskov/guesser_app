const BASE = "/api";

export async function fetchJson<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function postJson<T>(path: string, body: object): Promise<T> {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export interface Product {
  id: number;
  name: string;
  image_url: string;
  site: string;
  price?: number;
}

export interface Pair {
  left: Product;
  right: Product;
}
