import type { Point, Route } from '$lib/types';

/** The polyline of a route as a path, in the coordinates of the finished image. */
export function dOf(pts: Point[]): string {
	return 'M' + pts.map((p) => p[0] + ' ' + p[1]).join('L');
}

/** Where along the tour a per mille mark lands on the map.
 *
 * The third number of every point is exactly what makes this a lookup rather than a
 * second measurement.
 */
export function along(r: Route, t: number): [number, number] {
	const p = r.pts;
	let lo = 0;
	let hi = p.length - 1;
	while (lo < hi - 1) {
		const mid = (lo + hi) >> 1;
		if (p[mid][2] <= t) lo = mid;
		else hi = mid;
	}
	const span = p[hi][2] - p[lo][2];
	const f = span > 0 ? (t - p[lo][2]) / span : 0;
	return [p[lo][0] + (p[hi][0] - p[lo][0]) * f, p[lo][1] + (p[hi][1] - p[lo][1]) * f];
}

/** A German decimal, for the distances the reader sees. */
export function comma(v: number, digits: number): string {
	return v.toFixed(digits).replace('.', ',');
}
