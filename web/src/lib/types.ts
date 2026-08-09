/** The data contract with export_data.py.
 *
 * Every field here is written by that script and by nothing else. A field renamed on the
 * Python side without being renamed here is the one mistake that would otherwise stay
 * invisible until a map came out empty, which is the whole reason this file exists.
 */

/** A point on a route: x, y in pixels of the finished image, and the position along the
 *  tour in per mille — the third number is what ties the map to the elevation profile. */
export type Point = [number, number, number];

export interface Route {
	key: string;
	label: string;
	file: string;
	km: number;
	pts: Point[];
	/** present only when the GPX carried elevation */
	ele?: number[];
	lo?: number;
	hi?: number;
	ascent?: number;
}

export interface Mark {
	label: string;
	/** the icon name from collection.json — also the file name under icons/ */
	icon: string;
	/** the id in icons/sprite.svg, name and size, because the stroke clamps depend on size */
	sym: string;
	size: number;
	/** the point itself */
	x: number;
	y: number;
	/** the anchor of the label */
	ax: number;
	ay: number;
	side: 'l' | 'r' | 'c';
	/** highlights belong to a tour, endpoints do not */
	route?: string | null;
	km?: number;
}

export interface Collection {
	slug: string;
	name: string;
	subtitle: string[];
	cover: string;
	bg: string | null;
	label: string;
	view: [number, number];
	sup: number;
	/** rectangles the vector layer is clipped out of — the cartouche is painted over it */
	guard: [number, number, number, number][];
	routes: Route[];
	highlights: Mark[];
	endpoints: Mark[];
}

export interface CollectionSummary {
	slug: string;
	name: string;
	subtitle: string[];
	tours: number;
	highlights: number;
	cover: string;
	bg: string | null;
}

export interface ShippedFont {
	kind: 'label' | 'place';
	file: string;
	licence: string;
}

export interface Index {
	theme: { paper: string; ink: string; muted: string; accent: string };
	/** empty when the build machine had no licensed copy of Lora and Poppins */
	fonts: ShippedFont[];
	collections: CollectionSummary[];
}

export interface Icons {
	icons: string[];
}
