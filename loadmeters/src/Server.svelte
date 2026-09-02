<script>
	import { hslToHex, oscolors, cheight } from './stores.ts';
	import Tooltip from "./Tooltip.svelte";
	export let info
	export let hostname
	export let width = 200  // 固定幅
	
	// ウィンドウ高さに基づいてパネル高さを計算
	$: maxHeight = $cheight > 0 ? $cheight - 40 : (typeof window !== 'undefined' ? window.innerHeight - 40 : 600)  // パディング分を引く
	$: panelHeight = Math.max(info?.relc ? info.relc * maxHeight : 100, 100)
	
	// console.log("🔍 Server.svelte: Rendering", hostname, "height:", info?.relc, "history length:", info?.history?.length)

	let heights = []
	let colors = []
	$: {
		if (info && info.history && Array.isArray(info.history)) {
			for(let i=0;i<info.history.length; i++){
			if ( info.history[i] >= 0 ){
				let load = info.history[i] / info.cores
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
		} else {
			console.error("🔍 Server.svelte: Invalid info or history for", hostname, info)
		}
	}
</script>

<div class="panel" style="height: {panelHeight}px; width: {width}px;">
	<div class="name">
		{hostname} ({info?.relc ? (info.relc*100).toFixed(1) : '0'}%)
		<br><small>{panelHeight.toFixed(0)}px / {width.toFixed(0)}px</small>
	</div>
	<div class="links">
		<ul>
			{#if info.network && Array.isArray(info.network)}
				{#each info.network as net}
				<li><a class="link" href="ssh://{net.ip_address}">{net.ip_address}</a></li>
				{/each}
			{:else if info.address && Array.isArray(info.address)}
				{#each info.address as a}
				<li><a class="link" href="ssh://{a}">{a}</a></li>
				{/each}
			{/if}
		</ul>
	</div>
	<div class="os" style="background-color: {$oscolors[info.ostype]};">
		<!-- triangle -->
	</div>
	<div class="load">
		{#if info.history && Array.isArray(info.history)}
			{#each info.history as _,i}
			<!-- <div class="core" style="width:{width}px; height:{heights[i]*100}%; background-color: {colors[i]}"> -->
				<div class="core" style="height:{heights[i]*100}%; background-color: {colors[i]}">
				</div>
			{/each}
		{:else}
			<div class="error">No history data</div>
		{/if}
	</div>
	<Tooltip {info} />
</div>

<style>
	.panel {
		display: flex;
		flex-direction: column;
		padding: 0px;
		background-color: #ddd;
		border-radius: 15px;
		margin: 4px;
		-webkit-filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
		-moz-filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
  		-ms-filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
  		filter:drop-shadow(5px 5px 5px rgba(0, 0, 0, 0.2));
		position: relative;
		min-height: 100px;
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
		flex-wrap: nowrap;
		background-color: #000;
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
	.links {
		position: absolute;
		opacity: 0.5;
		width: 100%;
		/* height: 100%; */
		bottom: 0%;
		/* clip-path: polygon(0% 100%, 0% 0%, 100% 0%); */
		z-index: 322;
	}
	a.link {
		color: white;
	}
</style>
