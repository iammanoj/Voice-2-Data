import type { TableData } from "../hooks/useTableStream";

interface Props {
  table: TableData;
}

export function ComparisonTable({ table }: Props) {
  if (!table.title) {
    return (
      <div className="flex h-full items-center justify-center text-gray-600">
        <div className="text-center">
          <svg
            className="mx-auto mb-3 h-10 w-10 text-gray-700"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              d="M3 10h18M3 14h18M9 3v18M3 6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V6Z"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="text-sm">Data will appear here after analysis</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="mb-4 text-lg font-semibold text-gray-100">
        {table.title}
      </h3>

      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-900/50">
              <th className="px-4 py-3 text-left font-medium text-gray-400">
                Dimension
              </th>
              <th className="px-4 py-3 text-right font-medium text-gray-400">
                Previous
              </th>
              <th className="px-4 py-3 text-right font-medium text-gray-400">
                Current
              </th>
              <th className="px-4 py-3 text-right font-medium text-gray-400">
                Change
              </th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, i) => {
              const isNegative = row.delta.includes("-");
              return (
                <tr
                  key={i}
                  className={`
                    border-b border-gray-800/50 transition-colors
                    ${row.is_top_contributor ? "bg-red-950/20" : "hover:bg-gray-900/30"}
                  `}
                >
                  <td className="px-4 py-3 font-medium text-gray-200">
                    <div className="flex items-center gap-2">
                      {row.is_top_contributor && (
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500" />
                      )}
                      {row.dimension}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400">
                    {row.previous_value}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {row.current_value}
                  </td>
                  <td
                    className={`px-4 py-3 text-right font-semibold ${
                      isNegative ? "text-red-400" : "text-emerald-400"
                    }`}
                  >
                    {row.delta}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {table.rows.some((r) => r.is_top_contributor) && (
        <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500" />
          Top contributor to the change
        </div>
      )}
    </div>
  );
}
