<script lang="ts">
	import Card from '$lib/Card.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Maps for komoot collections</title>
</svelte:head>

<h1>Maps for komoot collections</h1>
<p class="lead">
	Drawn from the GPX exports of the tours — tinted paper, dashed paths, stamped woodland.
	Every map is 1600×1200 pixels and is rebuilt on each push to <code>main</code>.
</p>
<div class="grid">
	{#each data.index.collections as c (c.slug)}
		<Card {c} />
	{/each}
</div>
