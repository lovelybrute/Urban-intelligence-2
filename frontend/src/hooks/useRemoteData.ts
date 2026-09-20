import { useEffect, useState, useCallback } from "react";
import { DEMO_MODE, getAnalytics } from "../services/api";
export function useRemoteData<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(!DEMO_MODE);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (DEMO_MODE) return;
    let active = true;
    let pending = false;
    const load = async () => {
      if (pending) return;
      pending = true;
      try {
        const result = await getAnalytics<T>(path);
        if (active) {
          setData(result);
          setError("");
        }
      } catch {
        if (active) setError("Unable to retrieve this data. Try again.");
      } finally {
        pending = false;
        if (active) setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [path, revision]);
  const retry = useCallback(() => setRevision((v) => v + 1), []);
  return { data, error, loading, retry };
}
