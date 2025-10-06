// src/services/api.ts
const BASE = import.meta.env.REACT_APP_API_BASE || "http://localhost:8001";

export async function uploadFiles(files: File[]) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE}/upload/`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function processFiles() {
  const res = await fetch(`${BASE}/process/`, { method: "POST" });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error("Process failed: " + txt);
  }
  return res.json();
}

/**
 * fetchSpecs(view, strategy)
 *  - view: "merged" | "raw" (default "merged")
 *  - strategy: "priority" | "latest" (optional; backend must support it to change behaviour)
 *
 * Returns an array of rows. For merged view it's one row per parameter.
 * For raw view it may contain multiple rows for the same param (duplicate param names).
 */
export async function fetchSpecs(
  view: "merged" | "raw" = "merged",
  strategy?: "priority" | "latest" | "all"
) {
  let url = `${BASE}/specs/?view=${encodeURIComponent(view)}`;
  if (strategy) url += `&strategy=${encodeURIComponent(strategy)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const txt = await res.text();
    throw new Error("Failed to fetch specs: " + txt);
  }
  return res.json();
}

/**
 * saveSpecs expects an array of { param, value, unit }.
 * Will upsert USER overrides on the backend.
 */
export async function saveSpecs(
  specs: { param: string; value: string; unit: string }[]
) {
  const payload: any = {};
  specs.forEach((s) => {
    payload[s.param] = { value: s.value, unit: s.unit };
  });
  const res = await fetch(`${BASE}/update-specs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error("Save failed: " + txt);
  }
  return res.json();
}

export async function fetchDefects() {
  const res = await fetch(`${BASE}/defects/`);
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error("Failed to fetch defects");
  }
  return res.json();
}

export function downloadMasterCsv() {
  return `${BASE}/download/master`;
}
