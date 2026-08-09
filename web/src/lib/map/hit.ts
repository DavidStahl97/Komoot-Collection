import type { Route } from '$lib/types';

/** How near a pointer has to come to a line, in CSS pixels. */
export const PICK = 14;

export interface Hit {
	key: string;
	/** distance in map units */
	d: number;
	/** position along the tour in per mille */
	t: number;
}

/** Distance from a point to a segment, and how far along that segment the foot sits. */
export function segDist(
	px: number,
	py: number,
	ax: number,
	ay: number,
	bx: number,
	by: number
): { d: number; t: number } {
	const dx = bx - ax;
	const dy = by - ay;
	const l2 = dx * dx + dy * dy;
	let t = l2 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0;
	t = t < 0 ? 0 : t > 1 ? 1 : t;
	const qx = ax + t * dx - px;
	const qy = ay + t * dy - py;
	return { d: Math.sqrt(qx * qx + qy * qy), t };
}

/** Which tour a pointer means — one computation over the real lines.
 *
 * Not a stack of click paths: where two tours overlap both are reachable and the nearer
 * one wins, rather than whichever happened to be drawn last. A near tie goes to the tour
 * already picked, so a shared stretch does not flicker.
 */
export function nearest(
	routes: Route[],
	px: number,
	py: number,
	tol: number,
	sticky: string | null
): Hit | null {
	let best: Hit | null = null;
	for (const r of routes) {
		const pts = r.pts;
		let bd = Infinity;
		let bt = 0;
		for (let i = 1; i < pts.length; i++) {
			const s = segDist(px, py, pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]);
			if (s.d < bd) {
				bd = s.d;
				bt = pts[i - 1][2] + (pts[i][2] - pts[i - 1][2]) * s.t;
			}
		}
		if (!best || bd < best.d - 0.5 || (Math.abs(bd - best.d) <= 0.5 && r.key === sticky))
			best = { key: r.key, d: bd, t: bt };
	}
	return best && best.d <= tol ? best : null;
}
