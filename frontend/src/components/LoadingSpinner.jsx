export default function LoadingSpinner({ label = "불러오는 중입니다" }) {
  return (
    <div className="loading">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
