// src/components/SpecsTable.tsx
import { useEffect, useState } from "react";
import { saveSpecs } from "../services/api";

type Variant = {
  id?: number | string;
  param: string;
  value?: string | number | null;
  unit?: string | null;
  raw?: string | null;
  source?: string | null;
  origin?: string | null;
  priority?: number | null;
  uploaded_at?: string | null;
  // some backends use added_at or created_at
  added_at?: string | null;
  created_at?: string | null;
  [k: string]: any;
};

type Props = {
  specs: any; // can be array (merged) or object (all grouped) or array-of-variants
  onSaved: () => void;
  strategy: "priority" | "latest" | "all";
};

export default function SpecsTable({ specs, onSaved, strategy }: Props) {
  const [mergedRows, setMergedRows] = useState<Variant[]>([]);
  const [grouped, setGrouped] = useState<Record<string, Variant[]>>({});

  // Helpers to normalize many possible API shapes
  const toMergedArray = (inSpecs: any): Variant[] => {
    // If API already returned an array of { param, chosen, variants }
    if (Array.isArray(inSpecs) && inSpecs.length && "chosen" in inSpecs[0]) {
      return (inSpecs as any[]).map((item) => {
        const chosen = item.chosen ?? item;
        return {
          param: item.param,
          value: chosen?.value ?? "",
          unit: chosen?.unit ?? "",
          source: chosen?.source ?? "",
          origin: chosen?.origin ?? chosen?.meta?.filename ?? "",
          priority: chosen?.priority ?? chosen?.priority ?? 0,
          uploaded_at:
            chosen?.added_at ?? chosen?.uploaded_at ?? chosen?.created_at ?? "",
          raw: chosen?.raw ?? "",
        };
      });
    }

    // If API returned an object keyed by param with { chosen, variants }
    if (inSpecs && typeof inSpecs === "object" && !Array.isArray(inSpecs)) {
      return Object.entries(inSpecs).map(([param, info]: any) => {
        if (info && info.chosen) {
          const chosen = info.chosen;
          return {
            param,
            value: chosen?.value ?? "",
            unit: chosen?.unit ?? "",
            source: chosen?.source ?? "",
            origin: chosen?.origin ?? chosen?.meta?.filename ?? "",
            priority: chosen?.priority ?? 0,
            uploaded_at:
              chosen?.added_at ??
              chosen?.uploaded_at ??
              chosen?.created_at ??
              "",
            raw: chosen?.raw ?? "",
            variants: info.variants ?? [],
          };
        }
        // fallback: if info is an array of variants, choose first
        if (Array.isArray(info) && info.length) {
          const chosen = info[0];
          return {
            param,
            value: chosen?.value ?? "",
            unit: chosen?.unit ?? "",
            source: chosen?.source ?? "",
            origin: chosen?.origin ?? chosen?.meta?.filename ?? "",
            priority: chosen?.priority ?? 0,
            uploaded_at:
              chosen?.added_at ??
              chosen?.uploaded_at ??
              chosen?.created_at ??
              "",
            raw: chosen?.raw ?? "",
            variants: info,
          };
        }
        return {
          param,
          value: "",
          unit: "",
          source: "",
          origin: "",
          priority: 0,
          uploaded_at: "",
          raw: "",
        };
      });
    }

    // If API returned a flat array of rows (param+value)
    if (Array.isArray(inSpecs)) {
      return (inSpecs as any[]).map((r) => ({
        param: r.param ?? r.name ?? "",
        value: r.value ?? r.chosen?.value ?? "",
        unit: r.unit ?? r.chosen?.unit ?? "",
        source: r.source ?? r.chosen?.source ?? "",
        origin: r.origin ?? r.meta?.filename ?? "",
        priority: r.priority ?? r.chosen?.priority ?? 0,
        uploaded_at: r.uploaded_at ?? r.added_at ?? r.created_at ?? "",
        raw: r.raw ?? "",
      }));
    }

    // last resort: empty
    return [];
  };

  const toGrouped = (inSpecs: any): Record<string, Variant[]> => {
    // If backend returned mapping param -> array already, map directly
    if (inSpecs && typeof inSpecs === "object" && !Array.isArray(inSpecs)) {
      // Normalize values to arrays (they may already be)
      const out: Record<string, Variant[]> = {};
      Object.entries(inSpecs).forEach(([param, arr]: any) => {
        if (Array.isArray(arr)) {
          out[param] = arr.map((r: any) => ({
            param,
            ...r,
            value: r.value ?? r.chosen?.value ?? "",
            unit: r.unit ?? r.chosen?.unit ?? "",
            source: r.source ?? r.chosen?.source ?? "",
            origin: r.origin ?? r.meta?.filename ?? "",
            priority: r.priority ?? r.chosen?.priority ?? 0,
            uploaded_at: r.uploaded_at ?? r.added_at ?? r.created_at ?? "",
            raw: r.raw ?? r.chosen?.raw ?? "",
          }));
        } else if (arr && arr.chosen) {
          // support object with { chosen, variants }
          out[param] = (arr.variants ?? []).map((r: any) => ({
            param,
            ...r,
            value: r.value ?? r.chosen?.value ?? "",
            unit: r.unit ?? r.chosen?.unit ?? "",
            source: r.source ?? r.chosen?.source ?? "",
            origin: r.origin ?? r.meta?.filename ?? "",
            priority: r.priority ?? r.chosen?.priority ?? 0,
            uploaded_at: r.uploaded_at ?? r.added_at ?? r.created_at ?? "",
            raw: r.raw ?? r.chosen?.raw ?? "",
          }));
        } else {
          out[param] = [];
        }
      });
      return out;
    }

    // If inSpecs is an array of variants, group by param
    if (Array.isArray(inSpecs)) {
      const out: Record<string, Variant[]> = {};
      (inSpecs as any[]).forEach((r) => {
        const param = r.param ?? r.name ?? "";
        if (!out[param]) out[param] = [];
        out[param].push({
          param,
          value: r.value ?? r.chosen?.value ?? "",
          unit: r.unit ?? r.chosen?.unit ?? "",
          source: r.source ?? r.chosen?.source ?? "",
          origin: r.origin ?? r.meta?.filename ?? "",
          priority: r.priority ?? r.chosen?.priority ?? 0,
          uploaded_at: r.uploaded_at ?? r.added_at ?? r.created_at ?? "",
          raw: r.raw ?? r.chosen?.raw ?? "",
        });
      });
      return out;
    }

    return {};
  };

  // Normalize incoming props when specs or strategy change
  useEffect(() => {
    if (strategy === "all") {
      setGrouped(toGrouped(specs));
      setMergedRows([]);
    } else {
      setMergedRows(toMergedArray(specs));
      setGrouped({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [specs, strategy]);

  // Merge-mode editing handlers
  const handleMergedChange = (
    index: number,
    field: "value" | "unit",
    val: string
  ) => {
    setMergedRows((prev) => {
      const cp = [...prev];
      cp[index] = { ...cp[index], [field]: val };
      return cp;
    });
  };

  // Save merges: send one USER override per param currently shown
  const handleSaveMerged = async () => {
    try {
      // build one payload entry per unique param (use the last known row for that param)
      const payloadMap = new Map<
        string,
        { param: string; value: string; unit: string }
      >();
      mergedRows.forEach((r) => {
        const param = r.param;
        payloadMap.set(param, {
          param,
          value: String(r.value ?? ""),
          unit: String(r.unit ?? ""),
        });
      });
      const payload = Array.from(payloadMap.values());
      if (payload.length === 0) {
        alert("No specs to save.");
        return;
      }
      await saveSpecs(payload);
      alert("Saved USER overrides.");
      onSaved();
    } catch (err: any) {
      console.error("Save failed:", err);
      alert("Save failed: " + (err?.message ?? String(err)));
    }
  };

  // In 'all' grouped view, allow promoting a specific variant to USER override
  const handlePromoteVariant = async (param: string, variant: Variant) => {
    try {
      await saveSpecs([
        {
          param,
          value: String(variant.value ?? ""),
          unit: String(variant.unit ?? ""),
        },
      ]);
      alert(
        `Promoted ${param} = ${variant.value} ${variant.unit} as USER override.`
      );
      onSaved();
    } catch (err: any) {
      console.error("Promote failed:", err);
      alert("Promote failed: " + (err?.message ?? String(err)));
    }
  };

  const formatDate = (s?: string | null) => {
    if (!s) return "-";
    const d = new Date(s);
    if (isNaN(d.getTime())) return s;
    return d.toLocaleString();
  };

  // Render
  return (
    <div className="p-4 border rounded-lg shadow bg-white mt-4">
      <h2 className="text-xl font-bold mb-2">📑 Extracted Specifications</h2>

      {strategy === "all" ? (
        // Grouped (accordion) view
        <div>
          {Object.keys(grouped).length === 0 ? (
            <p className="text-sm text-gray-600">No specs available.</p>
          ) : (
            Object.entries(grouped).map(([param, variants]) => (
              <details key={param} className="mb-3 border rounded">
                <summary className="cursor-pointer px-3 py-2 bg-gray-100 font-semibold">
                  {param} ({variants.length} value
                  {variants.length > 1 ? "s" : ""})
                </summary>

                <div className="p-2">
                  <table className="table-auto w-full border text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-left">
                        <th className="px-2 py-1 border">Value</th>
                        <th className="px-2 py-1 border">Unit</th>
                        <th className="px-2 py-1 border">Source</th>
                        <th className="px-2 py-1 border">Origin</th>
                        <th className="px-2 py-1 border">Priority</th>
                        <th className="px-2 py-1 border">Uploaded At</th>
                        <th className="px-2 py-1 border">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {variants.map((v, i) => (
                        <tr key={`${param}-${v.id ?? i}`}>
                          <td className="px-2 py-1 border">
                            {String(v.value ?? "-")}
                          </td>
                          <td className="px-2 py-1 border">
                            {String(v.unit ?? "-")}
                          </td>
                          <td className="px-2 py-1 border">
                            {v.source ?? "-"}
                          </td>
                          <td className="px-2 py-1 border">
                            {v.origin ?? "-"}
                          </td>
                          <td className="px-2 py-1 border">
                            {v.priority ?? "-"}
                          </td>
                          <td className="px-2 py-1 border">
                            {formatDate(
                              v.uploaded_at ?? v.added_at ?? v.created_at
                            )}
                          </td>
                          <td className="px-2 py-1 border">
                            <button
                              onClick={() => handlePromoteVariant(param, v)}
                              className="px-2 py-1 bg-blue-600 text-black rounded text-sm"
                            >
                              Promote
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ))
          )}
        </div>
      ) : (
        // Merged/latest/priority view (one row per param, editable)
        <div>
          {mergedRows.length === 0 ? (
            <p className="text-sm text-gray-600">No specs available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="table-auto w-full border text-sm">
                <thead>
                  <tr className="bg-gray-100 text-left">
                    <th className="px-2 py-1 border">Parameter</th>
                    <th className="px-2 py-1 border">Value</th>
                    <th className="px-2 py-1 border">Unit</th>
                    <th className="px-2 py-1 border">Source</th>
                    <th className="px-2 py-1 border">Origin</th>
                    <th className="px-2 py-1 border">Uploaded At</th>
                    <th className="px-2 py-1 border">Raw</th>
                  </tr>
                </thead>
                <tbody>
                  {mergedRows.map((r, i) => (
                    <tr
                      key={`${r.param}-${i}`}
                      className={r.source === "USER" ? "bg-green-50" : ""}
                    >
                      <td className="px-2 py-1 border font-semibold text-gray-700">
                        {r.param}
                      </td>
                      <td className="px-2 py-1 border">
                        <input
                          className="w-full px-2 py-1 border rounded"
                          value={String(r.value ?? "")}
                          onChange={(e) =>
                            handleMergedChange(i, "value", e.target.value)
                          }
                        />
                      </td>
                      <td className="px-2 py-1 border">
                        <input
                          className="w-full px-2 py-1 border rounded"
                          value={String(r.unit ?? "")}
                          onChange={(e) =>
                            handleMergedChange(i, "unit", e.target.value)
                          }
                        />
                      </td>
                      <td className="px-2 py-1 border text-gray-500">
                        {r.source ?? "-"}
                      </td>
                      <td className="px-2 py-1 border text-gray-500">
                        {r.origin ?? "-"}
                      </td>
                      <td className="px-2 py-1 border text-gray-500">
                        {formatDate(
                          r.uploaded_at ?? r.added_at ?? r.created_at
                        )}
                      </td>
                      <td className="px-2 py-1 border text-gray-500 italic">
                        {String(r.raw ?? "-")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex justify-between items-center mt-3">
            <button
              onClick={handleSaveMerged}
              className="px-4 py-2 bg-green-600 text-black rounded hover:bg-green-700"
            >
              💾 Save Changes
            </button>
            <div className="text-sm text-gray-500">
              (Tip: Download master CSV after saving)
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
