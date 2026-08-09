import { base } from '$app/paths';
import type { Icons } from '$lib/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const res = await fetch(`${base}/data/icons.json`);
	if (!res.ok) throw new Error(`data/icons.json is missing (${res.status})`);
	return { icons: ((await res.json()) as Icons).icons };
};
