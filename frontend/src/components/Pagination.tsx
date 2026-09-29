interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, totalPages, total, onChange }: PaginationProps) {
  if (totalPages <= 1) {
    return <div className="pagination pagination-single">{total} record{total === 1 ? "" : "s"}</div>;
  }
  const pages: number[] = [];
  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
  for (let p = start; p < start + 5 && p <= totalPages; p += 1) {
    pages.push(p);
  }
  return (
    <div className="pagination">
      <span className="pagination-info">
        {total} record{total === 1 ? "" : "s"}
      </span>
      <div className="pagination-controls">
        <button type="button" className="btn btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          ‹ Prev
        </button>
        {pages.map((p) => (
          <button
            key={p}
            type="button"
            className={`btn btn-sm${p === page ? " btn-page-active" : ""}`}
            onClick={() => onChange(p)}
          >
            {p}
          </button>
        ))}
        <button
          type="button"
          className="btn btn-sm"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Next ›
        </button>
      </div>
    </div>
  );
}
