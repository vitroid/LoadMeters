<script>
	import ColorLegend from "./ColorLegend.svelte";
	import Servers from "./Servers.svelte";
	import StatusIndicator from "./StatusIndicator.svelte";
	import { uptime } from "./stores.ts";

	let online = true;

	uptime()

	setInterval(async () => {
		online = await uptime()
	}, 15*1000)  // every 15 seconds

</script>



<StatusIndicator {online}/>

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
