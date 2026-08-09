<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { Collection, Mark } from '$lib/types';
	import { dOf, along } from './geom';
	import { nearest, PICK } from './hit';
	import type { TourState } from './tour.svelte';
	import { MapView } from './view.svelte';

	interface Props {
		data: Collection;
		/** named `tour`, not `state` — a local binding called `state` would turn every
		 *  `$state` rune in this file into a store subscription */
		tour: TourState;
		/** the contents of icons/sprite.svg, already fetched */
		sprite: string;
	}
	let { data, tour, sprite }: Props = $props();

	// All derived from the prop rather than read once: navigating from one collection to
	// the next updates `data` in place, and a frame captured at init would be the previous
	// collection's.
	const VW = $derived(data.view[0]);
	const VH = $derived(data.view[1]);
	// the icons are recorded supersampled, exactly as the renderer draws them
	const ICON = $derived(1 / data.sup);
	const view = $derived(new MapView(data.view[0], data.view[1]));

	// Highlights and endpoints sit above the routes, exactly as the renderer stacks them —
	// which is why the line no longer has to be masked out from under icon and plate.
	const marks: { m: Mark; kind: string; pad: number }[] = $derived([
		...data.highlights.map((m) => ({ m, kind: 'spot', pad: 9 })),
		...data.endpoints.map((m) => ({ m, kind: 'place', pad: 14 }))
	]);

	// The vector layer keeps out of the cartouche, which is painted over it on the drawn map.
	const clipD = $derived(
		data.guard.length
			? `M0 0H${data.view[0]}V${data.view[1]}H0Z` +
					data.guard.map((g) => `M${g[0]} ${g[1]}h${g[2]}v${g[3]}h${-g[2]}Z`).join('')
			: null
	);
	const clipId = 'map-guard';

	let svgEl: SVGSVGElement | null = null;
	const textEls: SVGTextElement[] = [];
	const plateEls: SVGRectElement[] = [];

	const k = $derived(view.k);
	const active = $derived(tour.active);

	// the picked line belongs on top; keyed, so the nodes move instead of being rebuilt
	const ordered = $derived(
		active
			? [...data.routes.filter((r) => r.key !== active), ...data.routes.filter((r) => r.key === active)]
			: data.routes
	);

	const cursorAt = $derived.by(() => {
		const r = tour.profiled;
		return r && tour.cursor !== null ? along(r, tour.cursor) : null;
	});

	function anchor(side: string) {
		return side === 'c' ? 'middle' : side === 'r' ? 'start' : 'end';
	}

	/** The plate is measured, not calculated.
	 *
	 * The browser knows how wide its own text is, and the drawn map no longer carries a
	 * label this has to agree with. Twice, because before the web font has loaded the
	 * fallback gives a narrower box. Everything is laid out around the anchor at the
	 * origin, so the scale() in front of it does not drag the offsets along.
	 */
	function layout() {
		marks.forEach((entry, i) => {
			const text = textEls[i];
			const plate = plateEls[i];
			if (!text || !plate) return;
			text.setAttribute('y', '0');
			let bb: DOMRect;
			try {
				bb = text.getBBox();
			} catch {
				return;
			}
			// the renderer puts the top of the text at the anchor
			text.setAttribute('y', (-bb.y).toFixed(1));
			plate.setAttribute('x', (bb.x - entry.pad).toFixed(1));
			plate.setAttribute('y', '-5');
			plate.setAttribute('width', (bb.width + 2 * entry.pad).toFixed(1));
			plate.setAttribute('height', (bb.height + 12).toFixed(1));
		});
	}

	// ------------------------------------------------------------------ input
	// The bare wheel scrolls the page: a figure this wide that swallows it is unpleasant on
	// a laptop and impossible on a phone. Zooming is ctrl/⌘ plus wheel, pinch, double click
	// or the buttons.
	type Drag =
		| { mode: 'pan'; x: number; y: number }
		| { mode: 'pinch'; d: number; k: number };

	const pointers: Record<number, { x: number; y: number }> = {};
	// reactive, because the cursor over the sheet follows it
	let drag = $state<Drag | null>(null);
	let moved = 0;
	let over = $state(false);

	function pointerList() {
		return Object.values(pointers);
	}

	function atPointer(ev: { clientX: number; clientY: number }) {
		if (!svgEl) return null;
		const b = svgEl.getBoundingClientRect();
		if (!b.width || !b.height) return null;
		return {
			x: view.x + ((ev.clientX - b.left) / b.width) * view.w,
			y: view.y + ((ev.clientY - b.top) / b.height) * view.h,
			tol: (PICK * view.w) / b.width,
			sx: view.w / b.width,
			sy: view.h / b.height
		};
	}

	function onpointerdown(ev: PointerEvent) {
		pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
		svgEl?.setPointerCapture?.(ev.pointerId);
		const list = pointerList();
		moved = 0;
		drag =
			list.length === 1
				? { mode: 'pan', x: ev.clientX, y: ev.clientY }
				: {
						mode: 'pinch',
						d: Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y),
						k: view.k
					};
	}

	function onpointermove(ev: PointerEvent) {
		const p = atPointer(ev);
		if (!p) return;
		if (pointers[ev.pointerId]) {
			pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
			const list = pointerList();
			if (drag?.mode === 'pinch' && list.length >= 2 && svgEl) {
				const d = Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y);
				if (drag.d > 0) {
					const b = svgEl.getBoundingClientRect();
					const mx = view.x + (((list[0].x + list[1].x) / 2 - b.left) / b.width) * view.w;
					const my = view.y + (((list[0].y + list[1].y) / 2 - b.top) / b.height) * view.h;
					view.setZoom(drag.k * (d / drag.d), mx, my);
				}
				moved = 99;
				return;
			}
			if (drag?.mode === 'pan') {
				const dx = ev.clientX - drag.x;
				const dy = ev.clientY - drag.y;
				moved += Math.abs(dx) + Math.abs(dy);
				drag.x = ev.clientX;
				drag.y = ev.clientY;
				if (view.zoomed) {
					view.panBy(-dx * p.sx, -dy * p.sy);
					return;
				}
			}
		}
		const hit = nearest(data.routes, p.x, p.y, p.tol, tour.picked);
		tour.peek(hit ? hit.key : null);
		over = !!hit;
		// running along the line moves the cursor in the profile, and the other way round
		const prof = tour.profiled;
		tour.cursor = hit && prof && hit.key === prof.key ? hit.t : null;
	}

	function release(ev: PointerEvent) {
		delete pointers[ev.pointerId];
		if (!pointerList().length) drag = null;
	}

	function onpointerleave(ev: PointerEvent) {
		release(ev);
		tour.peek(null);
		tour.cursor = null;
		over = false;
	}

	function onclick(ev: MouseEvent) {
		if (moved > 6) return; // that was a drag, not a pick
		const p = atPointer(ev);
		const hit = p && nearest(data.routes, p.x, p.y, p.tol, tour.picked);
		tour.pick(hit && hit.key !== tour.picked ? hit.key : null);
	}

	function ondblclick(ev: MouseEvent) {
		const p = atPointer(ev);
		if (p) view.setZoom(view.k * (ev.shiftKey ? 1 / 2 : 2), p.x, p.y);
	}

	function onkeydown(ev: KeyboardEvent) {
		const step = view.w / 8;
		const pan: Record<string, [number, number]> = {
			ArrowLeft: [-step, 0],
			ArrowRight: [step, 0],
			ArrowUp: [0, -step],
			ArrowDown: [0, step]
		};
		if (pan[ev.key]) {
			view.panBy(pan[ev.key][0], pan[ev.key][1]);
			ev.preventDefault();
		} else if (ev.key === '+' || ev.key === '=') view.zoomBy(1.6);
		else if (ev.key === '-') view.zoomBy(1 / 1.6);
		else if (ev.key === '0') view.reset();
	}

	const cursorStyle = $derived.by(() =>
		drag?.mode === 'pan' && view.zoomed ? 'grabbing' : over ? 'pointer' : view.zoomed ? 'grab' : ''
	);

	// Measured after every render that changed the marks — on the first one, and again for
	// another collection. The second pass below is the web font arriving.
	$effect(() => {
		marks;
		layout();
	});

	onMount(() => {
		if (document.fonts?.ready) document.fonts.ready.then(layout);
		// not through the attribute, because preventDefault needs a non-passive listener
		const el = svgEl;
		const wheel = (ev: WheelEvent) => {
			if (!ev.ctrlKey && !ev.metaKey) return; // let the page scroll
			ev.preventDefault();
			const p = atPointer(ev);
			if (p) view.setZoom(view.k * Math.pow(0.9985, ev.deltaY), p.x, p.y);
		};
		el?.addEventListener('wheel', wheel, { passive: false });
		return () => el?.removeEventListener('wheel', wheel);
	});
</script>

<!-- the sprite export_data.py recorded from icons.py; <use> needs it in this document -->
{@html sprite}

<!-- The figure takes the keyboard so arrow keys, +, − and 0 move the map. The tour list
     below is the accessible way to pick one; this is the shortcut, not the only way in. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<figure
	class="mapfig"
	class:zoomed={view.zoomed}
	tabindex="0"
	role="group"
	aria-label={data.label}
	{onkeydown}
>
	<!-- The pointer is a shortcut, not the only way in: every tour is also a button in the
	     list below, which is what the keyboard and a screen reader use. -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<svg
		bind:this={svgEl}
		class="map"
		class:focus={!!active}
		viewBox={view.viewBox}
		role="img"
		aria-label={data.label}
		style:cursor={cursorStyle}
		{onpointerdown}
		{onpointermove}
		onpointerup={release}
		onpointercancel={release}
		{onpointerleave}
		{onclick}
		{ondblclick}
	>
		{#if clipD}
			<defs>
				<clipPath id={clipId} clipPathUnits="userSpaceOnUse">
					<path d={clipD} clip-rule="evenodd" />
				</clipPath>
			</defs>
		{/if}

		{#if data.bg}
			<!-- the paths in the data are relative to the site root, not to this page -->
			<image
				href="{base}/{data.bg}"
				x="0"
				y="0"
				width={VW}
				height={VH}
				preserveAspectRatio="none"
			/>
		{/if}
		<rect class="wash" x="0" y="0" width={VW} height={VH} />

		<g class="vec" clip-path={clipD ? `url(#${clipId})` : undefined}>
			<g class="routes">
				{#each ordered as r (r.key)}
					<g class="route" class:on={r.key === active} data-key={r.key}>
						<path class="casing" d={dOf(r.pts)} />
						<path class="dash" d={dOf(r.pts)} />
					</g>
				{/each}
			</g>

			<g class="marks">
				{#each marks as entry, i (entry.kind + i)}
					<g
						class="mark {entry.kind}"
						class:on={!entry.m.route || entry.m.route === active}
						data-route={entry.m.route ?? undefined}
					>
						<use
							class="sym"
							href="#ic-{entry.m.sym}"
							transform="translate({entry.m.x},{entry.m.y}) scale({(ICON / k).toFixed(4)})"
						/>
						<g class="lab" transform="translate({entry.m.ax},{entry.m.ay}) scale({(1 / k).toFixed(4)})">
							<rect class="plate" bind:this={plateEls[i]} rx="2" />
							<text bind:this={textEls[i]} x="0" y="0" text-anchor={anchor(entry.m.side)}>
								{entry.m.label}
							</text>
						</g>
					</g>
				{/each}
			</g>

			<g class="cursor" style:display={cursorAt ? '' : 'none'}>
				<circle
					r={(7 / k).toFixed(2)}
					cx={cursorAt ? cursorAt[0].toFixed(1) : 0}
					cy={cursorAt ? cursorAt[1].toFixed(1) : 0}
				/>
			</g>
		</g>

		<!-- transparent rather than absent: it still hit-tests, so the whole sheet drags -->
		<rect class="grab" x="0" y="0" width={VW} height={VH} />
	</svg>

	<div class="zoom">
		<button type="button" title="Zoom in" aria-label="Zoom in" onclick={() => view.zoomBy(1.6)}>
			+
		</button>
		<button
			type="button"
			title="Zoom out"
			aria-label="Zoom out"
			onclick={() => view.zoomBy(1 / 1.6)}
		>
			−
		</button>
		<button type="button" title="Whole map" aria-label="Whole map" onclick={() => view.reset()}>
			⤡
		</button>
	</div>
</figure>

<style>
	/* The painted background is an image, everything that means something is a vector on
	   top of it — so picking a tour is a class name, not a hole cut into a veil, and two
	   tours crossing is not a case that has to be handled. */
	.mapfig {
		position: relative;
		margin: 0 0 12px;
		border: 1px solid var(--rule);
		line-height: 0;
		background: var(--paper);
		aspect-ratio: 4 / 3;
	}
	.mapfig:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.map {
		display: block;
		width: 100%;
		height: auto;
		touch-action: none;
		-webkit-user-select: none;
		user-select: none;
	}
	.grab {
		fill: transparent;
	}

	.casing {
		fill: none;
		stroke: #fff;
		stroke-width: 7;
		stroke-dasharray: 14 10;
		stroke-linecap: butt;
		stroke-linejoin: round;
	}
	.dash {
		fill: none;
		stroke: var(--accent);
		stroke-width: 4;
		stroke-dasharray: 14 10;
		stroke-linecap: butt;
		stroke-linejoin: round;
	}
	.plate {
		fill: var(--plate);
	}
	.lab text {
		font: italic 26px 'map-label', Georgia, 'Times New Roman', serif;
		fill: var(--ink);
	}
	.place .plate {
		fill: var(--ink);
	}
	.place text {
		font: 30px 'map-place', 'Segoe UI', Helvetica, Arial, sans-serif;
		fill: var(--paper);
	}

	/* What marks the picked tour is that everything else steps back: a sheet of paper over
	   the painted map, and the other lines and highlights fading into it. Nothing is drawn
	   on top of the picked one — being the only thing left in front is the emphasis. */
	.wash {
		fill: var(--paper);
		opacity: 0;
		transition: opacity 0.35s ease;
	}
	.map.focus .wash {
		opacity: 0.58;
	}
	.route,
	.mark {
		transition: opacity 0.25s ease;
	}
	.map.focus .route {
		opacity: 0.13;
	}
	.map.focus .route.on {
		opacity: 1;
	}
	.map.focus .mark {
		opacity: 0.1;
	}
	.map.focus .mark.on {
		opacity: 1;
	}
	.cursor circle {
		fill: var(--accent);
		stroke: #fff;
		stroke-width: 2;
	}

	.zoom {
		position: absolute;
		top: 10px;
		right: 10px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.zoom button {
		width: 32px;
		height: 32px;
		font: 16px/1 Georgia, serif;
		cursor: pointer;
		background: var(--panel);
		color: var(--ink);
		border: 1px solid var(--rule);
	}
	.zoom button:hover,
	.zoom button:focus-visible {
		border-color: var(--accent);
	}

	@media (prefers-reduced-motion: reduce) {
		.wash,
		.route,
		.mark {
			transition: none;
		}
	}
</style>
