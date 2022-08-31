<script>
	import Server from "./Server.svelte";
	import { uptimes } from "./stores.ts";

	let u
	uptimes.subscribe(_=>{u=_})
</script>

<div>
    {#each Object.keys(u) as hostname}
	<Server {hostname} info={u[hostname]} />
    {/each}
</div>

<style>
	div {
		display: flex;
		flex-direction: row;
		flex-wrap: wrap;
	}
</style>
