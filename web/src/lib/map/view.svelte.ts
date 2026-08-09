/** The view is the viewBox.
 *
 * One coordinate system for the background image and the vectors, so nothing can drift
 * apart. Routes scale with the map — a line width is map content — while icons and plates
 * scale against it and keep their size on screen. Otherwise the labels would be the only
 * thing left at four times in, which is when you wanted to read what is under them.
 */
export const MAXK = 4;

export class MapView {
	x = $state(0);
	y = $state(0);
	w = $state(0);
	h = $state(0);

	constructor(
		readonly vw: number,
		readonly vh: number
	) {
		this.w = vw;
		this.h = vh;
	}

	/** the current magnification, 1 for the whole sheet */
	get k(): number {
		return this.vw / this.w;
	}

	get viewBox(): string {
		return [this.x, this.y, this.w, this.h].map((v) => v.toFixed(2)).join(' ');
	}

	get zoomed(): boolean {
		return this.w < this.vw - 0.5;
	}

	clamp() {
		this.x = Math.max(0, Math.min(this.vw - this.w, this.x));
		this.y = Math.max(0, Math.min(this.vh - this.h, this.y));
	}

	/** Zoom to k, keeping the point under the pointer where it is. */
	setZoom(k: number, ux: number, uy: number) {
		k = Math.max(1, Math.min(MAXK, k));
		const w = this.vw / k;
		const h = this.vh / k;
		this.x = ux - (ux - this.x) * (w / this.w);
		this.y = uy - (uy - this.y) * (h / this.h);
		this.w = w;
		this.h = h;
		this.clamp();
	}

	zoomBy(f: number) {
		this.setZoom(this.k * f, this.x + this.w / 2, this.y + this.h / 2);
	}

	reset() {
		this.setZoom(1, this.vw / 2, this.vh / 2);
	}

	panBy(dx: number, dy: number) {
		this.x += dx;
		this.y += dy;
		this.clamp();
	}
}
