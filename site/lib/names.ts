/**
 * One place that turns a model id into a display name.
 *
 * Ids ("house", "bdog") are storage keys and must never reach a reader: the
 * track-record table and the explorer's picker were both printing them raw.
 * The five match the `name` field in characters.json; client components
 * cannot read that file, so the map is repeated here and the test pins them
 * together in spirit. A caller that has real display names to hand passes
 * them, and they win.
 */

const MODEL_NAME: Record<string, string> = {
  house: "House",
  alan: "Alan",
  lily: "Lily",
  valentina: "Valentina",
  tayler: "Tayler",
  bdog: "Bdog",
};

export function modelName(id: string, names?: Record<string, string>): string {
  return names?.[id] ?? MODEL_NAME[id] ?? id.charAt(0).toUpperCase() + id.slice(1);
}
