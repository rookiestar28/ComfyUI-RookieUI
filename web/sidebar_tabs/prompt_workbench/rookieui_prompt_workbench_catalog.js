import { normalizeTokenText } from "./rookieui_prompt_workbench_tokens.js";

export function normalizeGroupTagEntry(entry) {
  const insertToken = normalizeTokenText(entry?.insert_token ?? entry?.tag ?? entry?.english_label ?? entry?.label);
  if (!insertToken) {
    return null;
  }
  const englishLabel = normalizeTokenText(entry?.english_label ?? entry?.tag ?? insertToken) || insertToken;
  const localLabel = normalizeTokenText(entry?.local_label ?? (entry?.label && entry.label !== englishLabel ? entry.label : ""));
  return {
    ...entry,
    id: normalizeTokenText(entry?.id ?? insertToken).toLowerCase(),
    tag: normalizeTokenText(entry?.tag ?? englishLabel) || englishLabel,
    label: normalizeTokenText(entry?.label ?? localLabel ?? englishLabel) || insertToken,
    local_label: localLabel,
    english_label: englishLabel,
    insert_token: insertToken,
  };
}

export function normalizeGroupTagGroups(catalogPayload) {
  const groups = Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups : [];
  return groups
    .map((group, groupIndex) => {
      const groupId = normalizeTokenText(group?.id) || `group-${groupIndex + 1}`;
      const rawSubgroups = Array.isArray(group?.subgroups) && group.subgroups.length
        ? group.subgroups
        : [
            {
              id: groupId,
              title: group?.title ?? `Group ${groupIndex + 1}`,
              tag_entries: Array.isArray(group?.tag_entries)
                ? group.tag_entries
                : Array.isArray(group?.tags)
                  ? group.tags.map((tag) => ({ tag, label: tag, insert_token: tag }))
                  : [],
            },
          ];
      const subgroups = rawSubgroups
        .map((subgroup, subgroupIndex) => {
          const rawEntries = Array.isArray(subgroup?.tag_entries)
            ? subgroup.tag_entries
            : Array.isArray(subgroup?.tags)
              ? subgroup.tags.map((tag) => ({ tag, label: tag, insert_token: tag }))
              : [];
          const tagEntries = rawEntries.map(normalizeGroupTagEntry).filter(Boolean);
          if (!tagEntries.length) {
            return null;
          }
          return {
            id: normalizeTokenText(subgroup?.id) || `${groupId}-${subgroupIndex + 1}`,
            title: normalizeTokenText(subgroup?.title) || normalizeTokenText(group?.title) || `Group ${groupIndex + 1}`,
            tag_entries: tagEntries,
          };
        })
        .filter(Boolean);
      if (!subgroups.length) {
        return null;
      }
      return {
        id: groupId,
        title: normalizeTokenText(group?.title) || `Group ${groupIndex + 1}`,
        subgroups,
        tag_entries: subgroups.flatMap((subgroup) => subgroup.tag_entries),
      };
    })
    .filter(Boolean);
}

export function getCatalogPayloadSlices(catalogPayload) {
  return {
    groups: Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups : [],
    sections: Array.isArray(catalogPayload?.prompt_library?.sections) ? catalogPayload.prompt_library.sections : [],
    tagcompleteEntries: Array.isArray(catalogPayload?.tagcomplete?.entries) ? catalogPayload.tagcomplete.entries : [],
    embeddings: Array.isArray(catalogPayload?.extra_networks?.embeddings) ? catalogPayload.extra_networks.embeddings : [],
    loras: Array.isArray(catalogPayload?.extra_networks?.loras) ? catalogPayload.extra_networks.loras : [],
  };
}

export function filterTagcompleteEntries(entries, query, limit = 24) {
  const normalizedQuery = normalizeTokenText(query).toLowerCase();
  return (Array.isArray(entries) ? entries : [])
    .filter((entry) => {
      if (!normalizedQuery) {
        return true;
      }
      const haystack = [
        entry?.tag,
        entry?.label,
        entry?.category,
        ...(Array.isArray(entry?.aliases) ? entry.aliases : []),
      ]
        .map((value) => String(value ?? "").toLowerCase())
        .join(" ");
      return haystack.includes(normalizedQuery);
    })
    .slice(0, limit);
}

export function renderPromptWorkbenchCatalogPane({
  catalogPane,
  catalogPayload,
  catalogSearchState,
  clearChildren,
  appendTextElement,
  createActionButton,
  idPrefix,
  getCatalogHighlight,
  appendPromptFragment,
  syncUi,
}) {
  clearChildren(catalogPane);
  const heading = document.createElement("div");
  heading.className = "rookieui-shell__prompt-workbench-pane-header";
  catalogPane.appendChild(heading);
  appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", "Catalog and Quick Insert");

  const { groups, sections, tagcompleteEntries, embeddings, loras } = getCatalogPayloadSlices(catalogPayload);

  const renderChipRow = (title, entries, fragmentBuilder, actionLabel = "Add") => {
    const block = document.createElement("section");
    block.className = "rookieui-shell__prompt-workbench-catalog-block";
    catalogPane.appendChild(block);
    appendTextElement(block, "h6", "rookieui-shell__prompt-workbench-pane-title", title);
    const chipGrid = document.createElement("div");
    chipGrid.className = "rookieui-shell__prompt-workbench-chip-grid";
    block.appendChild(chipGrid);
    if (!entries.length) {
      appendTextElement(
        chipGrid,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        `No ${title.toLowerCase()} entries are available for this workbench profile.`,
      );
      return;
    }
    entries.forEach((entry, index) => {
      const button = createActionButton(`${idPrefix}-${title.toLowerCase().replace(/\s+/g, "-")}-${index}`, actionLabel);
      button.classList.add("rookieui-shell__prompt-workbench-chip");
      if (entry?.highlight_class) {
        button.classList.add(String(entry.highlight_class));
      }
      button.dataset.highlight = getCatalogHighlight(entry);
      if (Array.isArray(entry?.aliases) && entry.aliases.length) {
        button.title = `Aliases: ${entry.aliases.join(", ")}`;
      }
      button.textContent = String(entry?.label ?? entry?.title ?? entry?.id ?? fragmentBuilder(entry));
      button.addEventListener("click", () => {
        appendPromptFragment(fragmentBuilder(entry), {
          statusMessage: `Inserted ${String(entry?.label ?? entry?.title ?? entry?.id ?? "catalog entry")}`,
        });
      });
      chipGrid.appendChild(button);
    });
  };

  const renderNetworkSelect = (title, entries, fragmentBuilder, actionLabel = "Insert") => {
    const block = document.createElement("section");
    block.className = "rookieui-shell__prompt-workbench-catalog-block";
    catalogPane.appendChild(block);
    appendTextElement(block, "h6", "rookieui-shell__prompt-workbench-pane-title", title);
    if (!entries.length) {
      appendTextElement(
        block,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        `No ${title.toLowerCase()} entries are available for this workbench profile.`,
      );
      return;
    }

    const slug = title.toLowerCase().replace(/\s+/g, "-");
    appendTextElement(
      block,
      "p",
      "rookieui-shell__prompt-workbench-empty",
      `${entries.length} ${entries.length === 1 ? "entry" : "entries"} available. Use the dropdown to keep large host inventories compact.`,
    );
    const controls = document.createElement("div");
    controls.className = "rookieui-shell__prompt-workbench-catalog-select-row";
    block.appendChild(controls);

    const select = document.createElement("select");
    select.id = `${idPrefix}-${slug}-select`;
    select.className = "rookieui-shell__select rookieui-shell__prompt-workbench-catalog-select";
    select.dataset.pwUi = "catalog-network-select";
    select.setAttribute("aria-label", `${title} catalog selector`);
    controls.appendChild(select);

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = `Select ${title}`;
    select.appendChild(placeholder);

    entries.forEach((entry, index) => {
      const option = document.createElement("option");
      option.id = `${idPrefix}-${slug}-option-${index}`;
      option.value = fragmentBuilder(entry);
      option.textContent = String(entry?.label ?? entry?.title ?? entry?.id ?? option.value);
      option.dataset.highlight = getCatalogHighlight(entry);
      if (Array.isArray(entry?.aliases) && entry.aliases.length) {
        option.title = `Aliases: ${entry.aliases.join(", ")}`;
      }
      select.appendChild(option);
    });

    const insertButton = createActionButton(`${idPrefix}-${slug}-${actionLabel.toLowerCase()}`, actionLabel);
    insertButton.classList.add("rookieui-shell__prompt-workbench-catalog-insert");
    insertButton.dataset.pwUi = "catalog-network-insert";
    insertButton.disabled = !select.value;
    controls.appendChild(insertButton);

    select.addEventListener("change", () => {
      insertButton.disabled = !select.value;
    });
    insertButton.addEventListener("click", () => {
      if (!select.value) {
        return;
      }
      appendPromptFragment(select.value, {
        statusMessage: `Inserted ${select.options[select.selectedIndex]?.textContent || "catalog entry"}`,
      });
    });
  };

  const tagcompleteBlock = document.createElement("section");
  tagcompleteBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
  catalogPane.appendChild(tagcompleteBlock);
  appendTextElement(tagcompleteBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Tagcomplete Lookup");
  const searchInput = document.createElement("input");
  searchInput.id = `${idPrefix}-tagcomplete-search`;
  searchInput.type = "search";
  searchInput.className = "rookieui-shell__input";
  searchInput.placeholder = "Search tags, aliases, or categories";
  searchInput.setAttribute("aria-label", "Search Prompt Workbench tagcomplete catalog");
  searchInput.value = catalogSearchState.query;
  searchInput.addEventListener("input", () => {
    catalogSearchState.query = String(searchInput.value ?? "");
    syncUi();
  });
  tagcompleteBlock.appendChild(searchInput);
  renderChipRow("Tagcomplete Matches", filterTagcompleteEntries(tagcompleteEntries, catalogSearchState.query), (entry) =>
    String(entry?.insert_token ?? entry?.tag ?? entry?.label ?? ""));

  groups.forEach((group, groupIndex) => {
    renderChipRow(
      String(group?.title ?? `Group ${groupIndex + 1}`),
      Array.isArray(group?.tag_entries)
        ? group.tag_entries
        : Array.isArray(group?.tags)
          ? group.tags.map((tag) => ({ id: tag, label: tag }))
          : [],
      (entry) => String(entry?.insert_token ?? entry?.tag ?? entry?.label ?? ""),
    );
  });

  sections.forEach((section, sectionIndex) => {
    const block = document.createElement("section");
    block.className = "rookieui-shell__prompt-workbench-catalog-block";
    catalogPane.appendChild(block);
    appendTextElement(
      block,
      "h6",
      "rookieui-shell__prompt-workbench-pane-title",
      String(section?.title ?? `Section ${sectionIndex + 1}`),
    );
    const list = document.createElement("div");
    list.className = "rookieui-shell__prompt-workbench-entry-list";
    block.appendChild(list);
    const entries = Array.isArray(section?.entries) ? section.entries : [];
    if (!entries.length) {
      appendTextElement(list, "p", "rookieui-shell__prompt-workbench-empty", "No prompt-library entries available.");
      return;
    }
    entries.forEach((entry, entryIndex) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-entry";
      list.appendChild(row);
      const copy = document.createElement("div");
      copy.className = "rookieui-shell__prompt-workbench-entry-copy";
      row.appendChild(copy);
      appendTextElement(copy, "strong", "rookieui-shell__prompt-workbench-entry-label", String(entry?.label ?? "Library Entry"));
      appendTextElement(copy, "p", "rookieui-shell__prompt-workbench-entry-text", String(entry?.prompt_text ?? ""));
      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-entry-actions";
      row.appendChild(controls);
      const appendButton = createActionButton(`${idPrefix}-library-append-${sectionIndex}-${entryIndex}`, "Append");
      appendButton.addEventListener("click", () => {
        appendPromptFragment(String(entry?.prompt_text ?? ""), {
          statusMessage: `Appended ${String(entry?.label ?? "library entry")}`,
        });
      });
      controls.appendChild(appendButton);
      const replaceButton = createActionButton(`${idPrefix}-library-replace-${sectionIndex}-${entryIndex}`, "Replace");
      replaceButton.addEventListener("click", () => {
        appendPromptFragment(String(entry?.prompt_text ?? ""), {
          replace: true,
          statusMessage: `Replaced prompt with ${String(entry?.label ?? "library entry")}`,
        });
      });
      controls.appendChild(replaceButton);
    });
  });

  renderNetworkSelect("Embeddings", embeddings, (entry) => String(entry?.insert_token ?? entry?.id ?? ""), "Insert");
  renderNetworkSelect("LoRAs", loras, (entry) => String(entry?.insert_token ?? entry?.id ?? ""), "Insert");
}
