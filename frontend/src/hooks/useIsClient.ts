"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

/**
 * React 19–safe hook that returns `true` only on the client after hydration.
 * Uses `useSyncExternalStore` to avoid `set-state-in-effect` and `refs-during-render` lint errors.
 */
export function useIsClient(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
