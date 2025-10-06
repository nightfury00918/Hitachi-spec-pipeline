// src/App.tsx
import { useEffect, useState } from "react";
import FileUpload from "./components/FileUpload";
import SpecsTable from "./components/SpecsTable";
import Loader from "./components/Loader";
import DefectsTable from "./components/DefectsTable";
import { fetchSpecs, fetchDefects, downloadMasterCsv } from "./services/api";

function App() {
  const [specs, setSpecs] = useState<any>([]);
  const [loading, setLoading] = useState(false);
  const [defects, setDefects] = useState<any[]>([]);

  // View toggles
  const [specView, setSpecView] = useState<"merged" | "raw">("merged");
  const [mergeStrategy, setMergeStrategy] = useState<
    "priority" | "latest" | "all"
  >("priority");

  const loadSpecs = async (view = specView, strategy = mergeStrategy) => {
    setLoading(true);
    try {
      const data = await fetchSpecs(view, strategy);
      setSpecs(data || []);
    } catch (err) {
      console.error("Fetch failed", err);
      alert("Failed to load specs: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadDefects = async () => {
    try {
      const d = await fetchDefects();
      setDefects(d);
    } catch (err) {
      console.error("Failed to load defects", err);
    }
  };

  const isEmptyObject = (obj) => {
    // First, ensure the input is a non-null object
    if (obj === null || typeof obj !== "object") {
      return false; // Or throw an error, depending on desired behavior
    }
    return Object.keys(obj).length === 0;
  };

  useEffect(() => {
    loadSpecs();
    loadDefects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // reload specs when view or strategy changes
  useEffect(() => {
    loadSpecs(specView, mergeStrategy);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [specView, mergeStrategy]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-3xl font-bold text-center mb-6 text-blue-700">
        ⚙️ Spec Extraction & Defect Mapping
      </h1>
      <div className="max-w-8xl mx-auto space-y-6">
        <FileUpload
          onUploaded={() => {
            loadSpecs(); // uses current view/strategy
            loadDefects();
          }}
        />

        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">Master Dataset</h2>

          <div className="flex items-center space-x-3">
            {/* View toggle */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setSpecView("merged")}
                className={`px-3 py-1 rounded text-sm ${
                  specView === "merged"
                    ? "bg-gray-600 text-blue-700"
                    : "bg-gray-200"
                }`}
              >
                Merged View
              </button>
              <button
                onClick={() => setSpecView("raw")}
                className={`px-3 py-1 rounded text-sm ${
                  specView === "raw"
                    ? "bg-blue-600 text-blue-700"
                    : "bg-gray-200"
                }`}
              >
                Raw View
              </button>
            </div>

            {/* Merge resolution strategy */}
            <select
              value={mergeStrategy}
              onChange={(e) =>
                setMergeStrategy(
                  e.target.value as "priority" | "latest" | "all"
                )
              }
            >
              <option value="priority">
                Priority (DOCX &gt; PDF &gt; Image)
              </option>
              <option value="latest">Latest (by upload time)</option>
              <option value="all">Show all overlaps</option>
            </select>

            <a
              href={downloadMasterCsv()}
              className="px-3 py-1 bg-gray-200 rounded text-sm"
              target="_blank"
              rel="noreferrer"
            >
              ⬇️ Download master CSV
            </a>
          </div>
        </div>

        {loading ? (
          <Loader />
        ) : (Array.isArray(specs) && specs.length) ||
          (!Array.isArray(specs) && !isEmptyObject(specs)) ? (
          <SpecsTable
            specs={specs}
            onSaved={loadSpecs}
            strategy={mergeStrategy}
          />
        ) : (
          <p className="text-center text-gray-600">
            No specs yet. Upload documents to get started.
          </p>
        )}

        <div>
          <h2 className="text-lg font-semibold mb-2">Defect Results</h2>
          <DefectsTable defects={defects} />
        </div>
      </div>
    </div>
  );
}

export default App;
