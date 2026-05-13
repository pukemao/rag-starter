export function parseOptionalJson(value: string): Record<string, unknown> | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("过滤条件必须是 JSON 对象");
  }
  return parsed as Record<string, unknown>;
}
