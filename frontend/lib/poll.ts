const FINISHED = new Set(["DONE", "REJECTED"]);
export const POLL_MS = 1500;
/** refetchInterval for an upload: keep polling until it is DONE or REJECTED. */
export const pollInterval = (status: string | undefined): number | false =>
  status && FINISHED.has(status) ? false : POLL_MS;
