import type { Collection, Route } from '$lib/types';

/** What the map, the tour list and the highlight table all read.
 *
 * Picking a tour is two class names and everything else follows — the caption, the
 * elevation profile, the rows that step back. Hovering is a preview and overrides the
 * pick without replacing it, which is why "hovered or picked" is one expression and not
 * two code paths.
 */
export class TourState {
	picked = $state<string | null>(null);
	hovered = $state<string | null>(null);
	/** position along the shown tour in per mille, or null */
	cursor = $state<number | null>(null);

	readonly byKey: Map<string, Route>;

	constructor(readonly data: Collection) {
		this.byKey = new Map(data.routes.map((r) => [r.key, r]));
	}

	get active(): string | null {
		return this.hovered ?? this.picked;
	}

	get route(): Route | null {
		const key = this.active;
		return (key && this.byKey.get(key)) || null;
	}

	/** the tour shown in the elevation profile — only one that actually has elevation */
	get profiled(): Route | null {
		const r = this.route;
		return r && r.ele && r.ele.length ? r : null;
	}

	/** how many highlights belong to a tour */
	count(key: string): number {
		return this.data.highlights.filter((h) => h.route === key).length;
	}

	pick(key: string | null) {
		this.picked = key && this.byKey.has(key) ? key : null;
	}

	peek(key: string | null) {
		this.hovered = key && this.byKey.has(key) ? key : null;
	}
}
