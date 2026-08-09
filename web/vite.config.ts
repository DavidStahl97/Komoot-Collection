import { sveltekit } from '@sveltejs/kit/vite';
import { SvelteKitPWA } from '@vite-pwa/sveltekit';
import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';

// The colors of the installed app are the colors the map is drawn in. export_data.py
// writes them out of map_cover.py; nothing here may write them down a second time.
let theme: Record<string, string>;
try {
	theme = JSON.parse(readFileSync(new URL('./src/generated/theme.json', import.meta.url), 'utf8'));
} catch {
	throw new Error(
		'web/src/generated/theme.json is missing — run `python3 export_data.py --png out` first.'
	);
}

export default defineConfig({
	define: {
		// what the footer names: the repository the page belongs to and when it was built
		__REPO__: JSON.stringify(process.env.GITHUB_REPOSITORY || 'DavidStahl97/Komoot-Collection'),
		__BUILT__: JSON.stringify(process.env.BUILD_DATE || '')
	},
	plugins: [
		sveltekit(),
		SvelteKitPWA({
			registerType: 'autoUpdate',
			manifest: {
				name: 'Maps for komoot collections',
				short_name: 'komoot maps',
				description:
					'Illustrated cover images for komoot collections — drawn from the GPX exports of the tours.',
				lang: 'en',
				start_url: './',
				scope: './',
				id: './',
				display: 'standalone',
				orientation: 'any',
				background_color: theme.paper,
				theme_color: theme.paper,
				icons: [
					{ src: 'pwa/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
					{ src: 'pwa/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
					{
						src: 'pwa/icon-maskable-512.png',
						sizes: '512x512',
						type: 'image/png',
						purpose: 'maskable'
					}
				]
			},
			workbox: {
				// everything export_data.py wrote plus everything the bundler emitted; the
				// cover images are 1600x1200 and go well past the 2 MB default
				globPatterns: ['**/*.{js,css,html,json,png,svg,ttf,txt,webmanifest}'],
				maximumFileSizeToCacheInBytes: 8 * 1024 * 1024
			}
		})
	]
});
