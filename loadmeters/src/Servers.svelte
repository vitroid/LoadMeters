<script>
	import Server from "./Server.svelte";
	import { cheight, cwidth, uptimes } from "./stores.ts";
	let u
	uptimes.subscribe(_=>{u=_})
</script>

<div bind:clientWidth={$cwidth} bind:clientHeight={$cheight}>
    {#each Object.keys(u).sort() as hostname}
	<Server {hostname} info={u[hostname]} />
    {/each}
</div>

<style>
	div {
		color: #888;
		display: flex;
		flex-direction: column;
		flex-wrap: wrap;
		background-color: #444;
		height: 100vh;
		width: auto;
	}
</style>
