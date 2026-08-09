<script lang="ts">
	import { base } from '$app/paths';
	import type { CollectionSummary } from '$lib/types';

	let { c }: { c: CollectionSummary } = $props();

	const href = $derived(`${base}/collections/${c.slug}/`);
	const meta = $derived(
		`${c.tours} tours` + (c.highlights ? `, ${c.highlights} highlights` : '')
	);
</script>

<article class="card">
	<div>
		<a {href}>
			<img src="{base}/{c.cover}" alt="Cover image of the collection {c.name}" loading="lazy" />
		</a>
		<h2><a {href}>{c.name}</a></h2>
		{#if c.subtitle.length}
			<p>{c.subtitle.join(' ')}</p>
		{/if}
		<p class="meta">{meta}</p>
	</div>
</article>

<style>
	.card {
		background: var(--panel);
		border: 3px solid var(--accent);
		padding: 12px;
	}
	.card > div {
		border: 1px solid var(--rule);
		padding: 16px;
		height: 100%;
	}
	.card img {
		display: block;
		width: 100%;
		height: auto;
		border: 1px solid var(--rule);
	}
	.card p {
		margin: 0 0 10px;
		color: var(--muted);
		font-style: italic;
	}
	.meta {
		margin: 0;
		font-size: 0.85rem;
		color: var(--muted);
		font-style: normal;
	}
</style>
