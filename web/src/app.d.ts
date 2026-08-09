/// <reference types="vite-plugin-pwa/info" />
/// <reference types="vite-plugin-pwa/client" />

declare global {
	namespace App {}

	/** replaced at build time by vite.config.ts */
	const __REPO__: string;
	const __BUILT__: string;
}

declare module '$generated/theme.json' {
	const theme: { paper: string; ink: string; muted: string; accent: string };
	export default theme;
}

export {};
