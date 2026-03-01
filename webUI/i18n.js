import { loadLocale } from "./data-client.js?v=__BUILD_VERSION__";

let activeLocale = "l_english";
let englishPack = {};
let localePack = {};

export async function setLocale(localeCode) {
  englishPack = await loadLocale("l_english");
  activeLocale = localeCode || "l_english";
  localePack = activeLocale === "l_english" ? englishPack : await loadLocale(activeLocale);
  return activeLocale;
}

export function getLocale() {
  return activeLocale;
}

export function t(key) {
  if (!key || typeof key !== "string") {
    return "";
  }
  if (Object.prototype.hasOwnProperty.call(localePack, key)) {
    return localePack[key];
  }
  if (Object.prototype.hasOwnProperty.call(englishPack, key)) {
    return englishPack[key];
  }
  return key;
}

export function tList(keys) {
  if (!Array.isArray(keys)) {
    return [];
  }
  return keys
    .filter((key) => typeof key === "string" && key.length > 0)
    .map((key) => t(key));
}

