import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// GitHub Pages does not serve from the domain root but from /<repository>/, so every
// generated URL has to carry that prefix. BASE_PATH wins, otherwise it is taken from the
// repository the workflow runs in; locally it stays empty.
const fromRepo = process.env.GITHUB_REPOSITORY
	? '/' + process.env.GITHUB_REPOSITORY.split('/')[1]
	: '';
const base = (process.env.BASE_PATH ?? fromRepo).replace(/\/$/, '');

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		// The three pages without a parameter are prerendered as empty shells, so GitHub
		// Pages answers them with a real 200. A collection is a parameter and is reached
		// through 404.html, which is how Pages is made to serve a single-page app.
		adapter: adapter({ fallback: '404.html', precompress: false, strict: false }),
		paths: { base, relative: false },
		alias: { $generated: 'src/generated' }
	}
};
