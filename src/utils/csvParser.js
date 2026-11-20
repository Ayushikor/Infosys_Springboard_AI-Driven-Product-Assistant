
export const MAX_FILE_BYTES = 2 * 1024 * 1024;

const ALLOWED_TYPES = ["csv", "json"];

const getFileType = (file) => {
  const extension = file.name.split(".").pop()?.toLowerCase();
  return ALLOWED_TYPES.includes(extension) ? extension : null;
};

const normalizeHeader = (value) =>
  String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");

const getValue = (record, aliases) => {
  const entries = Object.entries(record ?? {});
  const normalizedEntries = entries.map(([key, value]) => [
    normalizeHeader(key),
    value,
  ]);

  for (const alias of aliases) {
    const match = normalizedEntries.find(
      ([key]) => key === normalizeHeader(alias)
    );

    if (match && match[1] !== undefined && match[1] !== null) {
      return match[1];
    }
  }

  return "";
};

const parseCsvText = (text) => {
  const rows = [];
  let row = [];
  let cell = "";
  let insideQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      if (insideQuotes && nextChar === '"') {
        cell += '"';
        i += 1;
      } else {
        insideQuotes = !insideQuotes;
      }
    } else if (char === "," && !insideQuotes) {
      row.push(cell);
      cell = "";
    } else if (
      (char === "\n" || char === "\r") &&
      !insideQuotes
    ) {
      if (char === "\r" && nextChar === "\n") {
        i += 1;
      }

      row.push(cell);
      cell = "";

      if (row.some((value) => value.trim() !== "")) {
        rows.push(row);
      }

      row = [];
    } else {
      cell += char;
    }
  }

  if (insideQuotes) {
    throw new Error("CSV contains an unclosed quoted field.");
  }

  row.push(cell);

  if (row.some((value) => value.trim() !== "")) {
    rows.push(row);
  }

  if (rows.length < 2) {
    return [];
  }

  const headers = rows[0].map((header) =>
    normalizeHeader(header)
  );

  return rows.slice(1).map((values) => {
    const record = {};

    headers.forEach((header, index) => {
      record[header] = values[index] ?? "";
    });

    return record;
  });
};

const normalizeSentiment = (value) => {
  const sentiment = String(value ?? "").trim().toLowerCase();

  if (["positive", "negative", "neutral"].includes(sentiment)) {
    return sentiment;
  }

  return "neutral";
};

const normalizeRecord = (raw, index) => {
  const errors = [];

  const rawText = String(
    getValue(raw, ["raw_text", "message", "body", "description"])
  ).trim();

  const title = String(
    getValue(raw, ["title", "subject"])
  ).trim() || rawText.slice(0, 100);

  const id = String(
    getValue(raw, ["feedback_id", "id", "feedbackId"])
  ).trim();

  const source = String(
    getValue(raw, ["source_channel", "source", "channel"])
  ).trim();

  const timestamp = String(
    getValue(raw, ["timestamp", "createdAt", "created_at", "date"])
  ).trim();

  const customer = String(
    getValue(raw, ["customer", "customer_name", "user"])
  ).trim();

  const sentiment = normalizeSentiment(
    getValue(raw, ["sentiment"])
  );

  const theme = String(
    getValue(raw, ["theme", "category"])
  ).trim();

  const votesValue = Number(
    getValue(raw, ["votes", "vote_count"])
  );

  if (!rawText) {
    errors.push("Missing feedback text (raw_text or message).");
  }

  if (!title) {
    errors.push("Missing title.");
  }

  const record = {
    id: id || `import-${Date.now()}-${index + 1}`,
    title,
    message: rawText,
    customer: customer || "Unknown",
    source: source || "Import",
    sentiment,
    theme: theme || "Uncategorized",
    votes:
      Number.isFinite(votesValue) && votesValue >= 0
        ? Math.round(votesValue)
        : 0,
    createdAt: timestamp || new Date().toISOString(),
  };

  return {
    rowNumber: index + 1,
    record,
    errors,
  };
};

export const parseFeedbackFile = async (file) => {
  if (!file) {
    return {
      rows: [],
      fatal: "Please select a file.",
    };
  }

  const fileType = getFileType(file);

  if (!fileType) {
    return {
      rows: [],
      fatal: "Unsupported file type. Please upload a CSV or JSON file.",
    };
  }

  if (file.size > MAX_FILE_BYTES) {
    return {
      rows: [],
      fatal: `File is too large. Maximum allowed size is ${(
        MAX_FILE_BYTES / (1024 * 1024)
      ).toFixed(0)} MB.`,
    };
  }

  try {
    const text = await file.text();

    if (!text.trim()) {
      return {
        rows: [],
        fatal: "The selected file is empty.",
      };
    }

    let rawRecords = [];

    if (fileType === "json") {
      const parsed = JSON.parse(text);

      if (Array.isArray(parsed)) {
        rawRecords = parsed;
      } else if (
        parsed &&
        typeof parsed === "object" &&
        Array.isArray(parsed.feedback)
      ) {
        rawRecords = parsed.feedback;
      } else {
        return {
          rows: [],
          fatal:
            "Invalid JSON structure. Expected an array of records or an object containing a feedback array.",
        };
      }
    }

    if (fileType === "csv") {
      rawRecords = parseCsvText(text);
    }

    if (!rawRecords.length) {
      return {
        rows: [],
        fatal: "No records were found in the selected file.",
      };
    }

    const rows = rawRecords.map((record, index) => {
      if (
        !record ||
        typeof record !== "object" ||
        Array.isArray(record)
      ) {
        return {
          rowNumber: index + 1,
          record: {},
          errors: ["Invalid record format. Expected an object."],
        };
      }

      return normalizeRecord(record, index);
    });

    return {
      rows,
      fatal: null,
    };
  } catch (error) {
    return {
      rows: [],
      fatal:
        error instanceof SyntaxError
          ? "Invalid JSON. Please check the file format."
          : error.message || "Could not parse the selected file.",
    };
  }
};
