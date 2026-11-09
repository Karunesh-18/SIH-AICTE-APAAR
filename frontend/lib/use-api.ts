"use client";
import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, ApiError } from "./api";

/** GET wrapper: key is the path, errors are ApiError (check .status for 403/404). */
export function useApiQuery<T>(path: string | null, opts: Partial<UseQueryOptions<T, ApiError>> = {}) {
  return useQuery<T, ApiError>({
    queryKey: ["api", path],
    queryFn: () => api.get<T>(path as string),
    enabled: path !== null,
    retry: (n, e) => e.status >= 500 && n < 2,
    ...opts,
  });
}
