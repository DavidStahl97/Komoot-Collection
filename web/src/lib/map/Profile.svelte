<script lang="ts">
	import { comma } from './geom';
	import { PB, PH, PL, PR, PT, PW, profileGeom } from './profile';
	import type { TourState } from './tour.svelte';

	let { tour }: { tour: TourState } = $props();

	const g = $derived(profileGeom(tour.profiled));

	// which sample the cursor sits on, and where that is in the frame
	const cur = $derived.by(() => {
		const r = tour.profiled;
		if (!g || !r?.ele || tour.cursor === null) return null;
		const i = Math.max(0, Math.min(g.n - 1, Math.round((tour.cursor / 1000) * (g.n - 1))));
		return { i, x: g.X(i), ele: r.ele[i], km: r.km };
	});

	function onpointermove(ev: PointerEvent) {
		const b = (ev.currentTarget as SVGSVGElement).getBoundingClientRect();
		if (!b.width) return;
		const f = (((ev.clientX - b.left) / b.width) * PW - PL) / (PW - PL - PR);
		tour.cursor = Math.max(0, Math.min(1, f)) * 1000;
	}
</script>

{#if g}
	<figure class="profile">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<svg
			viewBox="0 0 {PW} {PH}"
			role="img"
			aria-label="Elevation profile of the picked tour"
			{onpointermove}
			onpointerleave={() => (tour.cursor = null)}
		>
			<path class="area" d={g.area} />
			<path class="line" d={g.line} />
			<line class="base" x1={PL} x2={PW - PR} y1={g.base} y2={g.base} />
			{#if cur}
				<line class="rule" y1={PT} y2={PH - PB} x1={cur.x.toFixed(1)} x2={cur.x.toFixed(1)} />
			{/if}
			<text class="tick" x={PL - 8} y={PT + 9} text-anchor="end">{g.hi} m</text>
			<text class="tick" x={PL - 8} y={PH - PB} text-anchor="end">{g.lo} m</text>
		</svg>
		<figcaption>
			<span>{g.lo}–{g.hi} m · {g.ascent} m of ascent, from the GPX track</span>
			<span class="read">
				{#if cur}
					· km {comma((cur.km * (tour.cursor ?? 0)) / 1000, 1)} · {cur.ele} m
				{/if}
			</span>
		</figcaption>
	</figure>
{/if}

<style>
	/* the elevation profile of the picked tour, its cursor tied to the map both ways */
	.profile {
		margin: 0 0 14px;
	}
	.profile svg {
		display: block;
		width: 100%;
		height: auto;
		background: var(--panel);
		border: 1px solid var(--rule);
	}
	.area {
		fill: var(--accent);
		fill-opacity: 0.16;
	}
	.line {
		fill: none;
		stroke: var(--accent);
		stroke-width: 1.5;
	}
	.base {
		stroke: var(--rule);
		stroke-width: 1;
	}
	.rule {
		stroke: var(--ink);
		stroke-width: 1;
	}
	.tick {
		font: 13px Georgia, serif;
		fill: var(--muted);
	}
	figcaption {
		font-size: 0.82rem;
		color: var(--muted);
		font-style: italic;
		padding-top: 5px;
	}
	.read {
		font-style: normal;
		color: var(--ink);
	}
</style>
