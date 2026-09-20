import { RefreshCw } from "lucide-react";
export function AnalyticsState({
  error,
  loading,
  retry,
}: {
  error: string;
  loading: boolean;
  retry: () => void;
}) {
  if (error)
    return (
      <div role="alert" className="inline-notice">
        {error}
        <button className="btn btn-secondary" onClick={retry}>
          <RefreshCw size={14} />
          Retry
        </button>
      </div>
    );
  if (loading)
    return (
      <div role="status" className="inline-notice">
        Retrieving observations…
      </div>
    );
  return null;
}
