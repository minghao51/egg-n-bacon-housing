/**
 * Load and verify the v2 observed-period pack in the browser.
 *
 * The loader fetches the manifest, checks the generation, then hashes each
 * payload's bytes before decoding them, so any consumer of this hook renders
 * numbers from bytes verified in the same request. It returns `null` while that
 * work is in flight, then the loader's own `ready` / `absent` / `invalid`
 * result — a consumer must treat `null` and `invalid` as "no numbers yet", never
 * as "no sales".
 *
 * Shared by `/explore` and `/dashboard/leaderboard` so both surfaces verify the
 * same way and neither invents a second fetch path.
 */

import { useEffect, useState } from "react";
import {
  loadObservedPack,
  type PackLoad,
} from "@/utils/observed-pack-loader";

export function useObservedPack(): PackLoad | null {
  const [packLoad, setPackLoad] = useState<PackLoad | null>(null);

  useEffect(() => {
    let cancelled = false;

    void loadObservedPack({ baseUrl: import.meta.env.BASE_URL })
      .then((load) => {
        if (!cancelled) setPackLoad(load);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPackLoad({
            state: "invalid",
            errors: [
              error instanceof Error
                ? error.message
                : "the published pack could not be loaded",
            ],
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return packLoad;
}
