import { base } from '$app/paths';
import { error } from '@sveltejs/kit';
import type { Collection } from '$lib/types';
import type { PageLoad } from './$types';

// A collection is a parameter, so this page is not prerendered — GitHub Pages reaches it
// through 404.html, the fallback adapter-static writes.
export const prerender = false;

export const load: PageLoad = async ({ fetch, params }) => {
	const res = await fetch(`${base}/data/${params.slug}.json`);
	if (!res.ok) error(404, `No collection called "${params.slug}".`);
	const collection = (await res.json()) as Collection;

	// the icons, recorded from icons.py — <use> can only reach them inside this document
	const sprite = await fetch(`${base}/icons/sprite.svg`)
		.then((r) => (r.ok ? r.text() : ''))
		.catch(() => '');

	return { collection, sprite };
};
