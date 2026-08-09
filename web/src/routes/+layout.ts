import { base } from '$app/paths';
import type { Index } from '$lib/types';
import type { LayoutLoad } from './$types';

// A single-page app: nothing is rendered on a server, the three pages without a parameter
// are prerendered as empty shells so GitHub Pages answers them with a real 200.
export const ssr = false;
export const prerender = true;
export const trailingSlash = 'always';

export const load: LayoutLoad = async ({ fetch }) => {
	const res = await fetch(`${base}/data/index.json`);
	if (!res.ok)
		throw new Error(
			`data/index.json is missing (${res.status}) — run python3 export_data.py --png out`
		);
	return { index: (await res.json()) as Index };
};
