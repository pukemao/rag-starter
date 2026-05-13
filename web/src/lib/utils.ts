import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score?: number | null) {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "N/A";
  }
  return score.toFixed(4);
}
