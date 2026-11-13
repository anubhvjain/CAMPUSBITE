export default function Pagination({ page, pages, total, onChange }) {
  if (!pages || pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="btn btn-sm btn-ghost" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Prev
      </button>
      <span>
        Page {page} of {pages} · {total} total
      </span>
      <button className="btn btn-sm btn-ghost" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next →
      </button>
    </nav>
  );
}
