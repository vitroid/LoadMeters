<script>
	import Server from "./Server.svelte";
	import { cheight, cwidth, uptimes } from "./stores.ts";
	let u
	uptimes.subscribe(_=>{u=_})
</script>

<div bind:clientWidth={$cwidth} bind:clientHeight={$cheight}>
    {#each Object.keys(u) as hostname}
	<Server {hostname} info={u[hostname]} />
    {/each}
</div>

<style>
	div {
		display: flex;
		flex-direction: column;
		flex-wrap: wrap;
		background-color: #444;
		height: 95vh;
		width: auto;
	}
</style>
