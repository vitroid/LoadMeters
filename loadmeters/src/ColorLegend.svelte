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
		/* settings for itself */
        position: absolute;
        bottom: 0%;
        /* left: 00%; */
        z-index: 10;
        /* width:400px;
        height:400px;
        margin-left:-200px;
        margin-top:-200px;
        z-index: 10; */

		/* settings for the contained */
		display: flex;
		flex-direction: row;
		flex-wrap: wrap;
	}
	.legend {
		border-radius: 10px;
		color: white;
		padding: 5px;
        z-index: 20;
	}
</style>
