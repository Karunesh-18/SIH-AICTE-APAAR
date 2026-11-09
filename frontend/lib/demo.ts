/** Demo logins show only when NEXT_PUBLIC_DEMO is exactly "1". */
export const demoEnabled = (v: string | undefined = process.env.NEXT_PUBLIC_DEMO) => v === "1";
