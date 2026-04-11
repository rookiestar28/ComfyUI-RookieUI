export function buildQueuePane(parent, bootstrapState, formRegistry, context) {
  const {
    appendTextElement,
    createList,
    createActionButton,
    applyCrossPanePayload,
  } = context;  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  appendTextElement(section, "h3", "rookieui-shell__section-title", "Queue and History");
  appendTextElement(
    section,
    "p",
    "rookieui-shell__status",
    `Queue remaining: ${bootstrapState.queue?.queue_remaining ?? 0}`,
    "rookieui-queue-remaining",
  );

  const statusNode = appendTextElement(
    section,
    "p",
    "rookieui-shell__status",
    "Idle",
    "rookieui-queue-status",
  );

  const list = createList("rookieui-queue-list");
  section.appendChild(list);

  const jobs = bootstrapState.queue?.jobs ?? [];
  if (!jobs.length) {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = "No queue or history items available.";
    list.appendChild(item);
    return;
  }

  jobs.forEach((job, index) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = `${job.id} (${job.status})`;
    list.appendChild(item);

    if (!job.reusable_outputs?.length) {
      return;
    }

    const actions = document.createElement("div");
    actions.className = "rookieui-shell__actions";
    item.appendChild(actions);

    const img2imgButton = createActionButton(`rookieui-reuse-img2img-${index}`, "Use as Img2Img");
    img2imgButton.addEventListener("click", () => {
      const applied = applyCrossPanePayload(
        formRegistry,
        "img2img",
        {
          image_asset: job.reusable_outputs[0],
          mode: "img2img",
          mask_asset: "",
        },
        { activate: false },
      );
      statusNode.textContent = applied
        ? `Applied ${job.reusable_outputs[0]} to img2img`
        : "Img2Img form is unavailable.";
    });
    actions.appendChild(img2imgButton);

    const inpaintButton = createActionButton(`rookieui-reuse-inpaint-${index}`, "Use as Inpaint");
    inpaintButton.addEventListener("click", () => {
      const applied = applyCrossPanePayload(
        formRegistry,
        "img2img",
        {
          image_asset: job.reusable_outputs[0],
          mode: "inpaint",
        },
        { activate: false },
      );
      statusNode.textContent = applied
        ? `Applied ${job.reusable_outputs[0]} to inpaint`
        : "Img2Img form is unavailable.";
    });
    actions.appendChild(inpaintButton);
  });
}
