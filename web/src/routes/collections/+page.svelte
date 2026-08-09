<script lang="ts">
	import Card from '$lib/Card.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Collections</title>
</svelte:head>

<h1>Collections</h1>
<p class="lead">
	One folder below <code>gpx/</code> per collection — its own map frame, its own highlights,
	its own cover image.
</p>
<div class="grid">
	{#each data.index.collections as c (c.slug)}
		<Card {c} />
	{/each}
</div>
