<script>
	import { oscolors } from './stores.ts';
	export let info
	export let hostname

	let squaresize
	let panelw
	let cores_in_row
	let colors

	$: {
		squaresize = Math.sqrt(info.mips)/4

		if ( info.cores < 32 ){
			cores_in_row = 4
		}
		else {
			cores_in_row = 8
		}
		panelw = cores_in_row*squaresize //padding

		colors = Array(info.cores)
		for(let i=0;i<info.cores; i++){
			if ( i < info.load ){
				colors[i] = "blue"
			}
			else{
				colors[i] = "black"
			}
		}

	}
</script>

<div class="panel" style="background-color: {$oscolors[info.ostype]}">
	<div class="name">
		{hostname}
	</div>
	<div class="load" style="width:{panelw}px">
		{#each Array(info.cores) as _,i}
		<div class="core" style="width:{squaresize}px; height:{squaresize}px; background-color: {colors[i]}">
		</div>
		{/each}
	</div>
</div>

<style>
	.panel {
		display: flex;
		flex-direction: column;
		padding: 10px;
		background-color: #ddd;
		height: auto;
		border-radius: 15px;
		margin: 2px;
	}
	.name {
		padding: 0 0 5px 0;
		color: white;
	}
	.load {
		display: flex;
		flex-wrap: wrap;
		flex-direction: row;
		/* padding: 10px; */
	}
	.core {
		border-radius: 5px;
		padding: 0;
		margin: 0;
	}
</style>
