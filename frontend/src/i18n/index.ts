/**
 * Locale Registry — the ONLY file to edit when adding a new language.
 *
 * To add a new locale:
 *  1. Create `src/i18n/xx_XX.ts` following the es_ES.ts structure (meta + translations).
 *  2. Add one import + one entry in the `locales` map below.
 *  That's it — the dropdown, context and backend header update automatically.
 */

import { es_ES, meta as es_ES_meta } from "./es_ES";
import { en_GB, meta as en_GB_meta } from "./en_GB";

export const locales = {
  es_ES: { translations: es_ES, ...es_ES_meta },
  en_GB: { translations: en_GB, ...en_GB_meta },
} as const;

export type LocaleKey = keyof typeof locales;

/** Default locale key */
export const DEFAULT_LOCALE: LocaleKey = "es_ES";
