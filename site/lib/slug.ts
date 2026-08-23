/**
 * Kept apart from `lib/data.ts` on purpose.
 *
 * That module reads the filesystem, so anything importing from it lands in the
 * server bundle. A client component needing only this one function would drag
 * `node:fs` into the browser and fail the build.
 */

/** "Arsenal v Coventry" -> "arsenal-v-coventry" */
export const fixtureSlug = (label: string) =>
  label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
