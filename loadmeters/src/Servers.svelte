<script>
	import Server from "./Server.svelte";
	import { cheight, cwidth, uptimes } from "./stores.ts";
	let u = {}
	let serverList = []
	
	uptimes.subscribe(_ => {
		u = _ || {}
		console.log("🔍 Servers.svelte: uptimes updated", typeof u, Object.keys(u), u)
		// 安全に配列を作成
		if (u && typeof u === 'object' && !Array.isArray(u)) {
			serverList = Object.keys(u).sort()
		} else {
			serverList = []
			console.error("🔍 Servers.svelte: u is not a valid object", u)
		}
	})
	
	$: serverCount = serverList.length
	
	// 実際に表示される列数を計算
	// 各サーバーの高さの合計から、実際の列数を推定
	let actualColumns = 1
	$: {
		if (serverCount > 0 && $cheight > 0) {
			// 各サーバーの高さを計算して累積し、画面高さを超えたら次の列
			let currentColumnHeight = 0
			let columns = 1
			const maxHeight = $cheight - 40 // パディング分を引く
			
			for (let hostname of serverList) {
				const server = u[hostname]
				if (server && server.relc) {
					const panelHeight = Math.max(server.relc * maxHeight, 100) + 8 // gap分も加算
					if (currentColumnHeight + panelHeight > maxHeight && currentColumnHeight > 0) {
						columns++
						currentColumnHeight = panelHeight
					} else {
						currentColumnHeight += panelHeight
					}
				}
			}
			actualColumns = columns
		}
	}
	
	// 実際の列数に基づいて各列の幅を計算
	$: panelWidth = $cwidth > 0 ? Math.max(($cwidth - 40 - (actualColumns - 1) * 8) / actualColumns, 150) : 200
	
	// $: console.log("🔍 Servers.svelte: servers:", serverCount, "columns:", actualColumns, "panelWidth:", panelWidth)
</script>

<div bind:clientWidth={$cwidth} bind:clientHeight={$cheight}>
    <!-- デバッグ情報（コメントアウト） -->
    <!-- <div class="debug-info">
        サーバー数: {serverCount} ({serverList.join(', ')})
    </div> -->
    {#each serverList as hostname}
        {#if u[hostname] && hostname}
            <Server {hostname} info={u[hostname]} width={panelWidth} />
        {:else}
            <div class="error-panel">Error: {hostname}</div>
        {/if}
    {/each}
</div>

<style>
	div {
		color: #888;
		display: flex;
		flex-direction: column;  /* 縦方向に並べる */
		flex-wrap: wrap;        /* 折り返しあり */
		align-items: flex-start; /* 各列の左端で揃える */
		align-content: flex-end; /* 全体を下端で揃える */
		background-color: #444;
		height: 100vh;
		width: 100%;
		gap: 4px;
		padding: 20px;
		box-sizing: border-box;
		overflow: hidden;  /* スクロールバーを防ぐ */
	}
	.debug-info {
		position: fixed;
		top: 10px;
		left: 10px;
		background: rgba(0, 0, 0, 0.8);
		color: white;
		padding: 10px;
		border-radius: 5px;
		font-size: 12px;
		z-index: 1000;
		pointer-events: none;
	}
	.error-panel {
		width: 200px;
		height: 100px;
		background: red;
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 4px;
	}
</style>
