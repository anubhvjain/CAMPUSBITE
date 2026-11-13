import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from './api/client';

/** Runs an async loader whenever deps change; exposes data/loading/error and a reload(). */
export function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  const latest = useRef(0);

  const run = useCallback(async () => {
    const id = ++latest.current;
    setState((s) => ({ ...s, loading: true, error: '' }));
    try {
      const data = await loader();
      if (id === latest.current) setState({ data, loading: false, error: '' });
    } catch (e) {
      if (id === latest.current) setState((s) => ({ ...s, loading: false, error: errorMessage(e) }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { ...state, reload: run, setData: (data) => setState((s) => ({ ...s, data })) };
}

export function useDebounced(value, delay = 350) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}
