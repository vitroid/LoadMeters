<script>
	import { oscolors } from "./stores.ts";

	let pal;
	oscolors.subscribe(_=>{
		pal=_;
	})
</script>

<div class="container">
    {#each Object.keys(pal) as os}
	<div class="legend" style="background-color: {pal[os]}" >
		{os}
	</div>
	{/each}
</div>

<style>
	.container {
		display: flex;
		flex-direction: row;
		flex-wrap: wrap;
	}
	.legend {
		border-radius: 10px;
		color: white;
		padding: 5px;
	}
</style>
