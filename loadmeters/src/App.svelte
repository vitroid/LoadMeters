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
