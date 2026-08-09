import type { Route } from '$lib/types';

/** The frame of the elevation profile, in its own coordinates. */
export const PW = 1000;
export const PH = 170;
export const PL = 46;
export const PR = 12;
export const PT = 12;
export const PB = 26;

export interface ProfileGeom {
	line: string;
	area: string;
	base: number;
	lo: number;
	hi: number;
	ascent: number;
	n: number;
	/** x of sample i */
	X: (i: number) => number;
}

/** The path of one elevation profile.
 *
 * One profile, re-pathed on every change instead of one hidden copy per tour: only ever
 * one is shown, and "hovered or picked" is the same expression the map runs on.
 */
export function profileGeom(r: Route | null): ProfileGeom | null {
	if (!r || !r.ele || !r.ele.length || r.lo === undefined || r.hi === undefined) return null;
	const ele = r.ele;
	const lo = r.lo;
	const hi = r.hi;
	const n = ele.length;
	const span = Math.max(1, hi - lo);
	const iw = PW - PL - PR;
	const ih = PH - PT - PB;
	const base = PT + ih;
	const X = (i: number) => PL + (i / (n - 1)) * iw;
	const Y = (v: number) => PT + (1 - (v - lo) / span) * ih;

	let line = '';
	for (let i = 0; i < n; i++)
		line += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(ele[i]).toFixed(1);

	return {
		line,
		area: line + 'L' + X(n - 1).toFixed(1) + ' ' + base + 'L' + PL + ' ' + base + 'Z',
		base,
		lo,
		hi,
		ascent: r.ascent ?? 0,
		n,
		X
	};
}
