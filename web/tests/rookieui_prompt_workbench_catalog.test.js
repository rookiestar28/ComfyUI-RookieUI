import { describe, expect, test } from "vitest";

import {
  filterTagcompleteEntries,
  getCatalogPayloadSlices,
  normalizeGroupTagGroups,
} from "../sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_catalog.js";

describe("Prompt Workbench catalog module", () => {
  test("normalizes flat and subgrouped Group Tags payloads for renderer ownership", () => {
    const groups = normalizeGroupTagGroups({
      group_tags: {
        groups: [
          { title: "Expression", tags: ["looking at viewer"] },
          {
            id: "scene",
            title: "Scene",
            subgroups: [
              {
                id: "camera",
                title: "Camera",
                tag_entries: [
                  {
                    id: "wide-shot",
                    tag: "wide shot",
                    label: "廣角",
                    local_label: "廣角",
                    english_label: "wide shot",
                    insert_token: "wide shot",
                  },
                ],
              },
            ],
          },
        ],
      },
    });

    expect(groups).toHaveLength(2);
    expect(groups[0].id).toBe("group-1");
    expect(groups[0].subgroups[0].tag_entries[0].insert_token).toBe("looking at viewer");
    expect(groups[1].subgroups[0].tag_entries[0]).toMatchObject({
      id: "wide-shot",
      local_label: "廣角",
      english_label: "wide shot",
      insert_token: "wide shot",
    });
  });

  test("extracts catalog slices and filters tagcomplete entries by label, tag, category, or alias", () => {
    const catalog = {
      prompt_library: { sections: [{ id: "quality" }] },
      tagcomplete: {
        entries: [
          { tag: "masterpiece", label: "Masterpiece", category: "quality", aliases: ["best quality"] },
          { tag: "portrait", label: "Portrait", category: "composition", aliases: ["face"] },
        ],
      },
      extra_networks: {
        embeddings: [{ id: "easynegative" }],
        loras: [{ id: "detail_lora" }],
      },
    };

    expect(getCatalogPayloadSlices(catalog)).toEqual({
      groups: [],
      sections: [{ id: "quality" }],
      tagcompleteEntries: catalog.tagcomplete.entries,
      embeddings: [{ id: "easynegative" }],
      loras: [{ id: "detail_lora" }],
    });
    expect(filterTagcompleteEntries(catalog.tagcomplete.entries, "best")).toEqual([catalog.tagcomplete.entries[0]]);
    expect(filterTagcompleteEntries(catalog.tagcomplete.entries, "face")).toEqual([catalog.tagcomplete.entries[1]]);
  });
});
