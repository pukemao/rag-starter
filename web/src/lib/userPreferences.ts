export type UserPreferences = {
  showRagReferences: boolean;
  chatBackgroundImage: string;
  chatBackgroundOpacity: number;
};

export const USER_PREFERENCES_KEY = "rag-starter.user.preferences";

export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  showRagReferences: true,
  chatBackgroundImage: "",
  chatBackgroundOpacity: 0.2
};

export function loadUserPreferences(): UserPreferences {
  try {
    const raw = localStorage.getItem(USER_PREFERENCES_KEY);
    if (!raw) {
      return DEFAULT_USER_PREFERENCES;
    }
    const parsed = JSON.parse(raw) as Partial<UserPreferences>;
    return {
      showRagReferences: typeof parsed.showRagReferences === "boolean" ? parsed.showRagReferences : true,
      chatBackgroundImage: typeof parsed.chatBackgroundImage === "string" ? parsed.chatBackgroundImage : "",
      chatBackgroundOpacity:
        typeof parsed.chatBackgroundOpacity === "number" ? clampOpacity(parsed.chatBackgroundOpacity) : DEFAULT_USER_PREFERENCES.chatBackgroundOpacity
    };
  } catch {
    return DEFAULT_USER_PREFERENCES;
  }
}

export function saveUserPreferences(preferences: UserPreferences) {
  try {
    localStorage.setItem(
      USER_PREFERENCES_KEY,
      JSON.stringify({
        ...preferences,
        chatBackgroundOpacity: clampOpacity(preferences.chatBackgroundOpacity)
      })
    );
  } catch {
    // Browser storage may reject large background images or private-mode writes.
  }
}

export function clampOpacity(value: number) {
  return Math.min(1, Math.max(0.05, value));
}
