/**
 * Model names render as names, never as ids.
 *
 * The track-record table printed its row keys ("house", "bdog") straight into
 * the Model column, and the explorer's picker offered the same. One map owns
 * the id-to-name translation, so a new model gets a name in one place or
 * arrives visibly title-cased rather than lowercase.
 */

import { describe, expect, it } from "vitest";
import { modelName } from "./names";

describe("modelName", () => {
  it("names the house", () => {
    expect(modelName("house")).toBe("House");
  });

  it("names the five as the character data writes them", () => {
    expect(modelName("alan")).toBe("Alan");
    expect(modelName("lily")).toBe("Lily");
    expect(modelName("valentina")).toBe("Valentina");
    expect(modelName("tayler")).toBe("Tayler");
    expect(modelName("bdog")).toBe("Bdog");
  });

  it("title-cases an id it has never met rather than leaking it", () => {
    expect(modelName("ensemble-v2")).toBe("Ensemble-v2");
  });

  it("prefers a supplied display name over the map", () => {
    expect(modelName("bdog", { bdog: "B-Dog" })).toBe("B-Dog");
  });
});
