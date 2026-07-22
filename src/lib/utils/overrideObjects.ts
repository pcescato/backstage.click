import { recursiveCloneObject } from "./objectFunctions";

function isPlainObject(value: any): boolean {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function normalizeOverrideValue(value: any): any {
  if (value === "") {
    return null;
  }

  if (Array.isArray(value)) {
    return value.map((item) => normalizeOverrideValue(item));
  }

  if (isPlainObject(value)) {
    const result: any = {};

    for (const key in value) {
      result[key] = normalizeOverrideValue(value[key]);
    }

    return result;
  }

  return value;
}

export default function overrideObjects(target: any, source: any): any {
  // Create a new object by shallow copying the target
  const result = recursiveCloneObject(target);

  // Iterate over all properties in the source object
  for (const key in source) {
    const sourceValue = normalizeOverrideValue(source[key]);

    if (
      sourceValue &&
      typeof sourceValue === "object" &&
      !Array.isArray(sourceValue) && // Ensure it's not an array
      result[key] &&
      typeof result[key] === "object"
    ) {
      // Recursively merge nested objects
      result[key] = overrideObjects(result[key], sourceValue);
    } else {
      // Otherwise, just overwrite or add the value in the result object
      result[key] = sourceValue;
    }
  }

  return result;
}
