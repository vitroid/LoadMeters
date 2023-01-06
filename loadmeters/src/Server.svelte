<script>
	// import { cwidth } from 'Servers.svelte';
	import { cheight, cwidth, hslToHex, oscolors } from './stores.ts';
	export let info
	export let hostname
	// import Viewport from 'svelte-viewport-info'

	let width = $cwidth / 6.5 / 60
	let heights = []
	let colors = []
	let fullheight
	let titleh
	let scale = ($cheight-titleh) / (4700*96)
	$: {
		// cwidth;
		width = $cwidth / 6.5 / 60
		scale = ($cheight-titleh) / (4700*96)

		fullheight = info.cores * info.mips * scale
		for(let i=0;i<info.load.length; i++){
			if ( info.load[i] >= 0 ){
				heights[i] = info.load[i] * info.mips * scale
				let load = info.load[i] / info.cores
				if ( load > 1 ){
					let h = 0
					let s = 100 // Math.exp(-load)*100
					let v = 100 - 50*Math.exp(-(load-1))
					colors[i] = hslToHex(h, s, v)
				}
				else{
					let h = 300 - 300*load
					let s = load*100
					let v = 50
					colors[i] = hslToHex(h, s, v)
				}
			}
			else{
				heights[i] = fullheight;
				colors[i] = hslToHex(0, 100, 50)
			}

		}
	}
</script>

<div class="panel" style="background-color: {$oscolors[info.ostype]}; width: {width*60}px">
	<div class="name" bind:clientHeight={titleh}>
		{hostname}
	</div>
	<div class="load" style="height: {fullheight}px;">
		{#each info.load as _,i}
		<div class="core" style="width:{width}px; height:{heights[i]}px; background-color: {colors[i]}">
		</div>
		{/each}
	</div>
</div>
<!-- {Viewport.Width} -->

<style>
	.panel {
		display: flex;
		flex-direction: column;
		padding: 0px;
		background-color: #ddd;
		height: auto;
		width: 120px;
		/* border-radius: 15px; */
		margin: 5px;
	}
	.name {
		padding: 5px;
		color: white;
	}
	.load {
		display: flex;
		background-color: #000;
		flex-wrap: wrap;
		flex-direction: row;
		/* padding: 10px; */
		/* margin-top: auto; */
	}
	.core {
		border-radius: 5px;
		padding: 0;
		margin: 0;
		margin-top: auto;
	}
</style>
