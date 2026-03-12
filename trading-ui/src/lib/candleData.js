const REQUIRED_CSV_COLUMNS = ["timestamp", "open", "high", "low", "close"];
const COLUMN_ALIASES = {
  time: "timestamp",
  date: "timestamp",
  datetime: "timestamp",
  open_price: "open",
  o: "open",
  high_price: "high",
  h: "high",
  low_price: "low",
  l: "low",
  close_price: "close",
  c: "close",
  volume: "volume",
  vol: "volume",
  tick_volume: "volume",
};

function normalizeHeaderName(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return COLUMN_ALIASES[normalized] || normalized;
}

export function normalizeCsvColumns(columns) {
  return (Array.isArray(columns) ? columns : []).map(normalizeHeaderName);
}

export function validateCsvColumns(columns) {
  const normalizedColumns = normalizeCsvColumns(columns);
  const missing = REQUIRED_CSV_COLUMNS.filter((column) => !normalizedColumns.includes(column));

  if (missing.length > 0) {
    throw new Error(`Missing required columns: ${missing.join(", ")}`);
  }

  return normalizedColumns;
}

export function previewCsvHeaders(csvText) {
  const firstLine = String(csvText || "")
    .split(/\r?\n/u)
    .find((line) => line.trim().length > 0);

  if (!firstLine) {
    throw new Error("CSV is empty.");
  }

  const headers = normalizeCsvColumns(firstLine.split(","));
  validateCsvColumns(headers);
  return headers;
}

export function toUnixSeconds(timestamp) {
  if (timestamp === null || timestamp === undefined || timestamp === "") {
    return null;
  }

  if (typeof timestamp === "number" && Number.isFinite(timestamp)) {
    if (timestamp >= 1e12) {
      return Math.floor(timestamp / 1000);
    }
    return Math.floor(timestamp);
  }

  const numeric = Number(timestamp);
  if (Number.isFinite(numeric)) {
    if (numeric >= 1e12) {
      return Math.floor(numeric / 1000);
    }
    if (numeric >= 1e9) {
      return Math.floor(numeric);
    }
  }

  const parsed = Math.floor(new Date(timestamp).getTime() / 1000);
  return Number.isFinite(parsed) ? parsed : null;
}

function toFiniteNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function pickFirstDefined(input, keys) {
  for (const key of keys) {
    if (input?.[key] !== undefined && input?.[key] !== null && input?.[key] !== "") {
      return input[key];
    }
  }

  return undefined;
}

export function normalizeCandle(input) {
  if (!input || typeof input !== "object") {
    return null;
  }

  const time = toUnixSeconds(pickFirstDefined(input, ["time", "timestamp", "date", "datetime"]));
  const open = toFiniteNumber(pickFirstDefined(input, ["open", "open_price", "o"]));
  const high = toFiniteNumber(pickFirstDefined(input, ["high", "high_price", "h"]));
  const low = toFiniteNumber(pickFirstDefined(input, ["low", "low_price", "l"]));
  const close = toFiniteNumber(pickFirstDefined(input, ["close", "close_price", "c"]));
  const volume = toFiniteNumber(pickFirstDefined(input, ["volume", "vol", "tick_volume"])) ?? 0;

  if (
    time === null ||
    open === null ||
    high === null ||
    low === null ||
    close === null
  ) {
    return null;
  }

  return { time, open, high, low, close, volume };
}

export function normalizeSignal(signal) {
  if (!signal || typeof signal !== "object") {
    return null;
  }

  const time = toUnixSeconds(signal.time ?? signal.timestamp);
  if (time === null) {
    return null;
  }

  return { ...signal, time };
}

export function normalizeCandles(dataset, context = "candles") {
  if (!Array.isArray(dataset) || dataset.length === 0) {
    return [];
  }

  const deduped = new Map();
  let invalidRows = 0;

  dataset.forEach((item) => {
    const candle = normalizeCandle(item);
    if (!candle) {
      invalidRows += 1;
      return;
    }
    deduped.set(candle.time, candle);
  });

  const normalized = [...deduped.values()].sort((left, right) => left.time - right.time);

  if (invalidRows > 0) {
    console.warn(`[${context}] Dropped ${invalidRows} invalid candles during normalization.`);
  }

  if (normalized.length > 0) {
    console.log(`[${context}] dataset preview`, normalized.slice(0, 5));
  } else {
    console.warn(`[${context}] No valid candles available after normalization.`);
  }

  return normalized;
}
