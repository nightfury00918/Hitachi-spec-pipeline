// src/components/DefectsTable.tsx
interface Defect {
  [key: string]: any;
}

export default function DefectsTable({ defects }: { defects: Defect[] }) {
  if (!defects || defects.length === 0) {
    return <p className="text-gray-600">No defect results available.</p>;
  }

  // Dynamically determine columns from the first row
  const columns = Object.keys(defects[0]);

  return (
    <div className="p-4 border rounded-lg shadow bg-white mt-4">
      <h2 className="text-xl font-bold mb-2">🩺 Defect Mapping Results</h2>
      <div className="overflow-x-auto">
        <table className="w-full table-auto text-sm border">
          <thead>
            <tr className="bg-gray-100 text-left">
              {columns.map((col) => (
                <th
                  key={col}
                  className={`px-2 py-1 border font-medium ${
                    col === "decision" ? "text-center text-red-600" : ""
                  }`}
                >
                  {col.replace(/_/g, " ").toUpperCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {defects.map((d, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td
                    key={col}
                    className={`px-2 py-1 border ${
                      col === "decision"
                        ? "font-bold text-center bg-yellow-100"
                        : ""
                    }`}
                  >
                    {d[col] ?? "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
