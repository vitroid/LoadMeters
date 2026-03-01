<script>
	import { oscolors } from './stores.ts';
	export let info

	let usage
	$: {
		usage = "<ul>"
		for(let user in info.usage){
			usage += "<li>" + user + ":" + (info.usage[user]/100).toFixed(0) + "</li>"
		}
		usage += "</ul>"
	}
</script>

<div class="tooltip-container">
</div>
<!-- Hoverした時に表示されるもの。-->
<div class="tooltip-item" style="background-color: {$oscolors[info.ostype]};">
    <!-- IP:	{info.address}<br /> -->
    OS: {info.ostype}<br />
    bogoMIPS: {info.mips.toFixed(0)}<br />
	{#if ("GFlops" in info)}
	MFlops / 1core: {(info.GFlops*1000 / info.cores).toFixed(0)}<br />
	{/if}
    Cores: {info.cores}<br />
    {@html usage}
    {#if info.gpu}
    GPU:
    <ul>
        {#each info.gpu as gpu}
        <li>{gpu}</li>
        {/each}
    </ul>
    {/if}
</div>

<style>
	.tooltip-item {
		color: #fff;
		display: block;
		opacity: 0;
		padding: 5px;
		/* padding: .25rem .75rem; */
		position: absolute;
		/* transform: translateX(-50%); */
		transition: opacity .3s;
		/* width: 7rem; */
		z-index: 319;
        font-size: 80%;
	}
	/* これを一番上にしておかないと、ホバーが検出できない。 */
	.tooltip-container {
		position: absolute;
		width: 100%;
		height: 30px;
		background-color: gray;
		opacity: 0.2;
		z-index: 320;
	}
	.tooltip-container:hover + .tooltip-item {
		opacity: 1;
	}
</style>
