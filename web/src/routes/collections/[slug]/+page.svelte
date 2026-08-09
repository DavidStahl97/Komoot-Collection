<script lang="ts">
	import { replaceState } from '$app/navigation';
	import { base } from '$app/paths';
	import MapView from '$lib/map/Map.svelte';
	import Profile from '$lib/map/Profile.svelte';
	import { comma } from '$lib/map/geom';
	import { TourState } from '$lib/map/tour.svelte';
	import type { Mark } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const c = $derived(data.collection);

	// Recreated when the collection changes; the picked tour comes out of the address, so a
	// single tour can be linked to.
	const tour = $derived.by(() => {
		const s = new TourState(data.collection);
		const key = (globalThis.location?.hash ?? '').replace(/^#tour-/, '');
		if (key) s.pick(key);
		return s;
	});

	const intro =
		'Pick a tour to follow it on its own — click it again to bring the whole collection back.';
	const caption = $derived.by(() => {
		const r = tour.route;
		if (!r) return intro;
		const n = tour.count(r.key);
		const h = n === 0 ? 'no highlights' : n === 1 ? 'one highlight' : `${n} highlights`;
		return `${r.label} — ${comma(r.km, 1)} km, ${h}`;
	});

	const meta = $derived(
		`${c.routes.length} tours` + (c.highlights.length ? `, ${c.highlights.length} highlights` : '')
	);
	const rows = $derived([...c.highlights, ...c.endpoints]);

	function where(m: Mark) {
		return m.km != null ? `${m.route} at km ${m.km.toFixed(1)}` : 'fixed coordinate';
	}

	$effect(() => {
		const p = tour.picked;
		replaceState(p ? `#tour-${p}` : location.pathname + location.search, {});
	});
</script>

<svelte:head>
	<title>{c.name}</title>
</svelte:head>

<svelte:window onkeydown={(e) => e.key === 'Escape' && tour.pick(null)} />

<h1>{c.name}</h1>
{#if c.subtitle.length}
	<p class="lead">{c.subtitle.join(' ')}</p>
{/if}

<!-- With the background the map is built as vectors; without it the page is what it always
     was, an image and a link. -->
{#if c.bg}
	<MapView data={c} {tour} sprite={data.sprite} />
{:else}
	<figure class="mapfig">
		<img src="{base}/{c.cover}" alt="Cover image of the collection {c.name}" />
	</figure>
{/if}

<p class="caption" aria-live="polite">{caption}</p>

{#if c.bg}
	<Profile {tour} />
{/if}

<p class="actions">
	<a href="{base}/{c.cover}" download>Download cover image (PNG)</a>
	<span class="meta">{meta}</span>
</p>

<h2>Tours</h2>
<ul class="tours">
	{#each c.routes as r, i (r.key)}
		<li>
			<button
				type="button"
				data-key={r.key}
				aria-pressed={tour.picked === r.key}
				onclick={() => tour.pick(tour.picked === r.key ? null : r.key)}
				onmouseenter={() => tour.peek(r.key)}
				onmouseleave={() => tour.peek(null)}
				onfocus={() => tour.peek(r.key)}
				onblur={() => tour.peek(null)}
			>
				<span class="no">{i + 1}</span>
				<span>{r.label}</span>
				<span class="km">{comma(r.km, 1)} km</span>
			</button>
		</li>
	{/each}
</ul>

{#if rows.length}
	<h2>Highlights and endpoints</h2>
	<table>
		<thead>
			<tr><th></th><th>Label</th><th>Location</th></tr>
		</thead>
		<tbody>
			{#each rows as m, i (m.label + i)}
				<tr class:dim={!!tour.active && !!m.route && m.route !== tour.active}>
					<td><img src="{base}/icons/{m.icon}.png" alt="" /></td>
					<td>{m.label}</td>
					<td>{where(m)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
{/if}

<style>
	.mapfig {
		margin: 0 0 12px;
		border: 1px solid var(--rule);
		line-height: 0;
	}
	.mapfig img {
		display: block;
		width: 100%;
		height: auto;
	}
	.caption {
		margin: 0 0 26px;
		font-size: 0.9rem;
		color: var(--muted);
		font-style: italic;
		min-height: 1.4em;
	}
	.actions .meta {
		margin-left: 14px;
		font-size: 0.85rem;
		color: var(--muted);
	}
	.tours {
		list-style: none;
		margin: 0 0 10px;
		padding: 0;
		display: grid;
		gap: 10px;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
	}
	.tours button {
		width: 100%;
		display: flex;
		align-items: baseline;
		gap: 10px;
		font: inherit;
		text-align: left;
		cursor: pointer;
		background: var(--panel);
		color: var(--ink);
		border: 1px solid var(--rule);
		padding: 10px 12px;
	}
	.tours button:hover,
	.tours button:focus-visible {
		border-color: var(--accent);
	}
	.tours button[aria-pressed='true'] {
		border-color: var(--accent);
		background: var(--pressed);
		box-shadow: inset 3px 0 0 var(--accent);
	}
	.tours .no {
		color: var(--accent);
		font-size: 0.85rem;
		letter-spacing: 0.08em;
	}
	.tours .km {
		margin-left: auto;
		color: var(--muted);
		font-size: 0.85rem;
		font-style: italic;
	}
	tr {
		transition: opacity 0.25s ease;
	}
	tr.dim {
		opacity: 0.35;
	}
	@media (prefers-reduced-motion: reduce) {
		tr {
			transition: none;
		}
	}
</style>
