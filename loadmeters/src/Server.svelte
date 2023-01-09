<script>
	import { hslToHex, oscolors } from './stores.ts';
	export let info
	export let hostname


	let heights = []
	let colors = []
	$: {
		for(let i=0;i<info.load.length; i++){
			if ( info.load[i] >= 0 ){
				let load = info.load[i] / info.cores
				heights[i] = load
				if ( load > 1 ){
					heights[i] = 1.0
					let h = 0
					let s = 100 // Math.exp(-load)*100
					let v = 100 - 50*Math.exp(-(load-1))
					colors[i] = hslToHex(h, s, v)
				}
				else{
					let h = 300 - 300*load
					let s = load*100
					let v = i/2+30;
					colors[i] = hslToHex(h, s, v)
				}
			}
			else{
				heights[i] = 1.0
				colors[i] = hslToHex(0, 100, 20)
			}
		}
	}
	const tips=info.ostype
</script>

<div class="panel" style="height: {info.relc*100}%" tip-text={tips} tip-bg={$oscolors[info.ostype]}>
	<div class="name">
		{hostname}
	</div>
	<div class="os" style="background-color: {$oscolors[info.ostype]};">
		<!-- triangle -->
	</div>
	<div class="load">
		{#each info.load as _,i}
		<!-- <div class="core" style="width:{width}px; height:{heights[i]*100}%; background-color: {colors[i]}"> -->
			<div class="core" style="height:{heights[i]*100}%; background-color: {colors[i]}">
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
		/* border-radius: 15px; */
		margin: 4px;
		-webkit-filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
		-moz-filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
  		-ms-filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
  		filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
		position: relative;
	}
	/* .panel {
		position: absolute;
		bottom: 0%;
		right: 0%;
		border-bottom: 1px dashed #000;
		z-index:11;
		font-size: 200%;
		margin-right: 5px;
	} */

	.panel:before {
		content: attr(tip-text);
		position: absolute;
		font-size: 100%;

		top: 20px;
		left: 0%;

		background-color: attr(tip-bg);
		color: #fff;
		text-align: left;
		padding: 5px;

		display: none;
		z-index:12;

		opacity:0;
		transition:1s opacity;
	}
	.panel:hover:before {
 		display:block;
		opacity:1;
	}

	.name {
		position: absolute;
		top: 0px;
		padding: 5px;
		color: white;
		text-overflow: ellipsis;
		z-index: 4;
	}
	.load {
		display: flex;
		background-color: #000;
		flex-wrap: wrap;
		flex-direction: row;
		height: 100%;
		width: 100%;
		/* border-radius: 13px; */
		/* padding: 10px; */
		/* margin-top: auto; */
	}
	.core {
		/* border-radius: 5px; */
		padding: 0;
		margin: 0;
		margin-top: auto;
		width: 1.667%;
	}
	.os {
		position: absolute;
		width: 30px;
		height: 30px;
		clip-path: polygon(0% 100%, 0% 0%, 100% 0%);
		z-index: 2;
	}
</style>
