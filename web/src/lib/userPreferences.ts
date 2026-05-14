export type UserPreferences = {
  showRagReferences: boolean;
  chatBackgroundImage: string;
  chatBackgroundOpacity: number;
};

export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  showRagReferences: true,
  chatBackgroundImage: "",
  chatBackgroundOpacity: 0.2
};

export function clampOpacity(value: number) {
  return Math.min(1, Math.max(0.05, value));
}
