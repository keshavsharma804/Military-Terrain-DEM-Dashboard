// components/MetadataTable.jsx
function MetadataTable({ data }) {
  if (!data || !Array.isArray(data.features)) return null;

  return (
    <div className="mt-4 p-4 border rounded bg-white shadow">
      <h3 className="text-lg font-semibold mb-2">Metadata Preview</h3>
      <table className="table-auto w-full text-left text-sm">
        <thead>
          <tr>
            <th>Feature</th>
            <th>Type</th>
            <th>Coordinates</th>
          </tr>
        </thead>
        <tbody>
          {data.features.slice(0, 5).map((f, idx) => (
            <tr key={idx}>
              <td>{f.properties?.name || `Feature ${idx + 1}`}</td>
              <td>{f.geometry?.type}</td>
              <td>{JSON.stringify(f.geometry?.coordinates)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
