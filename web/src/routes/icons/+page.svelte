<script lang="ts">
	import { base } from '$app/paths';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Icons</title>
</svelte:head>

<h1>Icons</h1>
<p class="lead">
	The icons from <code>icons.py</code>, each drawn with PIL primitives. The function name is
	also the value of <code>"icon"</code> in the <code>collection.json</code>. Every icon is
	shown twice: stamped as a pixel image for the cover map, and recorded as SVG for the
	interactive map. Both come from the same function — where the two differ, the recorder in
	<code>svgdraw.py</code> is wrong.
</p>

<div class="icons">
	{#each data.icons as name (name)}
		<figure class="icon">
			<div class="pair">
				<span>
					<img src="{base}/icons/{name}.png" alt="Icon {name}" loading="lazy" />
					<em>PIL</em>
				</span>
				<span>
					<img src="{base}/icons/{name}.svg" alt="Icon {name} as vector" loading="lazy" />
					<em>SVG</em>
				</span>
			</div>
			<figcaption><code>{name}</code></figcaption>
		</figure>
	{/each}
</div>

<style>
	.icons {
		display: grid;
		gap: 22px;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
	}
	.icon {
		background: var(--panel);
		border: 1px solid var(--rule);
		padding: 12px;
		text-align: center;
		margin: 0;
	}
	.icon img {
		display: block;
		width: 100%;
		height: auto;
		background: var(--paper);
	}
	/* stamped and recorded side by side — the pair is the check that svgdraw.py still
	   draws what icons.py draws; there is no other test for it */
	.pair {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
	}
	.pair em {
		display: block;
		font-size: 0.68rem;
		font-style: normal;
		color: var(--muted);
		letter-spacing: 0.08em;
	}
	.icon code {
		font-size: 0.85rem;
		color: var(--ink);
	}
	.icon span {
		display: block;
		font-size: 0.78rem;
		color: var(--muted);
		font-style: italic;
	}
</style>
