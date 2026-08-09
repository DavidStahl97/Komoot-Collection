<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>{page.status} — Maps for komoot collections</title>
</svelte:head>

<h1>{page.status}</h1>
<p class="lead">{page.error?.message ?? 'This page does not exist.'}</p>
<p><a href="{base}/collections/">All collections</a></p>
