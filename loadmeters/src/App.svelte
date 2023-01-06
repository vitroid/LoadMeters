<script>
	import ColorLegend from "./ColorLegend.svelte";
	import Servers from "./Servers.svelte";
	import { uptime } from "./stores.ts";

	uptime()

	setInterval(() => {
		uptime()
	}, 6*1000)  // every one minute

</script>


<main>
	<Servers />
	<ColorLegend />
</main>

<style>
	main {
		display: flex;
		flex-direction: column;
		flex-wrap: wrap;
		height: 100vh;

		background-color: #333;
	}
</style>
