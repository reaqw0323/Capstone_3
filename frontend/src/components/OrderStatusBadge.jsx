export default function OrderStatusBadge({ status }) {
  const className = `status-badge status-${String(status).replace(/\s/g, "-")}`;
  return <span className={className}>{status}</span>;
}
