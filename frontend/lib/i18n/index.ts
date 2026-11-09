import en from "./en.json";
import hi from "./hi.json";

export type Lang = "en" | "hi";
const dict: Record<Lang, Record<string, string>> = { en, hi };

export const t = (lang: Lang, key: string): string => dict[lang][key] ?? dict.en[key] ?? key;
