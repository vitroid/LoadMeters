<script>
	import { disks, hslToHex, palette } from "./stores.ts";

	export let width = 200

	const MIN_SEG_PX = 8

	let data = {}
	disks.subscribe(_ => {
		data = _ || {}
	})

	$: hostnames = Object.keys(data).sort()

	$: maxTotal = hostnames.reduce((m, h) => {
		const vols = (data[h] && data[h].volumes) || []
		for (let v of vols) {
			if (v.total > m) m = v.total
		}
		return m
	}, 0)

	$: alerts = hostnames.filter(h => {
		const d = data[h]
		if (!d || d.reachable === false) return false
		return d.raid && d.raid.ok === false
	})

	$: rows = hostnames.reduce((acc, hostname) => {
		const d = data[hostname]
		const vols = (d && d.volumes) || []
		if (!vols.length) {
			acc.push({ hostname, vol: null, d })
			return acc
		}
		for (let i = 0; i < vols.length; i++) {
			acc.push({ hostname, vol: vols[i], d })
		}
		return acc
	}, [])

	function fmtBytes(n) {
		if (!n || n <= 0) return "0"
		const u = ["B", "KB", "MB", "GB", "TB", "PB"]
		let i = 0
		let x = n
		while (x >= 1024 && i < u.length - 1) {
			x /= 1024
			i++
		}
		return x.toFixed(i === 0 ? 0 : 1) + u[i]
	}

	function userList(vol) {
		const users = (vol && vol.users) || {}
		return Object.keys(users)
			.map(name => ({ name, bytes: users[name] }))
			.filter(u => u.bytes > 0)
			.sort((a, b) => b.bytes - a.bytes)
	}

	$: colorByUser = (() => {
		const map = {}
		for (let h of hostnames) {
			const vols = (data[h] && data[h].volumes) || []
			for (let v of vols) {
				for (let name of Object.keys((v && v.users) || {})) {
					if (!(name in map)) {
						map[name] = palette(Object.keys(map).length)
					}
				}
			}
		}
		return map
	})()

	function volWidthPct(vol) {
		if (!vol || maxTotal <= 0 || !vol.total) return 100
		return Math.max(4, (vol.total / maxTotal) * 100)
	}

	function usedPct(vol) {
		return vol && vol.total > 0 ? Math.min(100, (vol.used / vol.total) * 100) : 0
	}

	function volBarPx(vol) {
		return Math.max(1, width * volWidthPct(vol) / 100)
	}

	function segments(vol, colors) {
		if (!vol || !vol.used || vol.used <= 0) return []
		const used = vol.used
		const usedPx = volBarPx(vol) * (used / Math.max(vol.total, used))
		const people = userList(vol)
		const shown = []
		const tiny = []
		let accounted = 0
		const colorOf = (name) => (colors && colors[name]) || palette(0)
		for (let u of people) {
			accounted += u.bytes
			const px = usedPx * (u.bytes / used)
			if (px >= MIN_SEG_PX) {
				shown.push({
					id: u.name,
					label: u.name,
					bytes: u.bytes,
					pct: (u.bytes / used) * 100,
					color: colorOf(u.name),
					users: [u]
				})
			} else {
				tiny.push(u)
			}
		}
		const leftover = Math.max(0, used - accounted)
		if (tiny.length === 1) {
			const u = tiny[0]
			shown.push({
				id: u.name,
				label: u.name,
				bytes: u.bytes,
				pct: (u.bytes / used) * 100,
				color: colorOf(u.name),
				users: [u]
			})
		} else if (tiny.length > 1) {
			const bytes = tiny.reduce((s, u) => s + u.bytes, 0)
			shown.push({
				id: "__others",
				label: `others (${tiny.length})`,
				bytes,
				pct: (bytes / used) * 100,
				color: hslToHex(40, 8, 32),
				users: tiny
			})
		}
		if (leftover > used * 0.01) {
			const px = usedPx * (leftover / used)
			if (px >= 2 || shown.length === 0) {
				shown.push({
					id: "__rest",
					label: people.length ? "unaccounted" : "used",
					bytes: leftover,
					pct: (leftover / used) * 100,
					color: hslToHex(210, 35, 38),
					users: []
				})
			}
		}
		if (shown.length === 0) {
			shown.push({
				id: "__used",
				label: "used",
				bytes: used,
				pct: 100,
				color: hslToHex(210, 45, 42),
				users: []
			})
		}
		return shown
	}

	function raidLabel(d) {
		if (!d) return ""
		if (d.reachable === false) return "unreachable"
		return (d.raid && d.raid.status) || ""
	}

	function isBad(d) {
		return d && d.reachable !== false && d.raid && d.raid.ok === false
	}

	function isDown(d) {
		return !d || d.reachable === false
	}

	function isWarn(d) {
		return !isBad(d) && !isDown(d) && d.raid && d.raid.warnings && d.raid.warnings.length > 0
	}

	function fmtTemp(t) {
		return t === null || t === undefined ? "" : t + "°C"
	}

	function fmtAgo(ts) {
		if (!ts) return ""
		const s = Math.max(0, Date.now() / 1000 - ts)
		if (s < 120) return Math.round(s) + "s ago"
		if (s < 7200) return Math.round(s / 60) + "min ago"
		return Math.round(s / 3600) + "h ago"
	}

	function diskTitle(disk) {
		const parts = [`slot ${disk.slot}: ${disk.state}`, disk.vendor, disk.model, disk.serial, disk.size, fmtTemp(disk.temperature)]
		for (let k of Object.keys(disk.errors || {})) parts.push(`${k} ${disk.errors[k]}`)
		return parts.filter(Boolean).join("  ")
	}

	function diskSummary(disks) {
		const counts = {}
		for (let disk of disks) counts[disk.state] = (counts[disk.state] || 0) + 1
		return Object.keys(counts).map(s => `${counts[s]} ${s}`).join(", ")
	}

	function maxTemp(disks) {
		const ts = disks.map(disk => disk.temperature).filter(t => t !== null && t !== undefined)
		return ts.length ? Math.max(...ts) : null
	}

	function noteworthyDisks(disks) {
		return disks.filter(disk => !disk.ok || (disk.warnings && disk.warnings.length) || Object.keys(disk.errors || {}).length)
	}

	let hover = null
	let hideTimer = null

	$: hd = hover ? data[hover.hostname] : null
	$: raid = (hd && hd.raid) || {}
	$: tipDisks = raid.disks || []
	$: ctrl = raid.controller

	function portalTip(node, rect) {
		document.body.appendChild(node)
		function place(r) {
			if (!r) return
			const tw = node.offsetWidth
			const th = node.offsetHeight
			let left = r.left + (r.right - r.left) / 2 - tw / 2
			left = Math.min(Math.max(8, left), window.innerWidth - tw - 8)
			let top = r.top - th - 8
			if (top < 8) top = Math.min(r.bottom + 8, window.innerHeight - th - 8)
			node.style.left = left + "px"
			node.style.top = top + "px"
		}
		node.style.left = "-9999px"
		node.style.top = "0px"
		requestAnimationFrame(() => place(rect))
		return {
			update(r) { requestAnimationFrame(() => place(r)) },
			destroy() {
				if (node.parentNode) node.parentNode.removeChild(node)
			}
		}
	}

	function rectOf(el) {
		const r = el.getBoundingClientRect()
		return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }
	}

	function showRowTip(e, row) {
		keepTip()
		const rowRect = rectOf(e.currentTarget)
		hover = { hostname: row.hostname, seg: null, rowRect, rect: rowRect }
	}

	function showSegTip(e, row, seg) {
		keepTip()
		const rowRect = rectOf(e.currentTarget.closest(".row"))
		hover = { hostname: row.hostname, seg, rowRect, rect: rectOf(e.currentTarget) }
	}

	function leaveSeg() {
		if (hover) hover = { ...hover, seg: null, rect: hover.rowRect }
	}

	function delayHide() {
		if (hideTimer) clearTimeout(hideTimer)
		hideTimer = setTimeout(() => {
			hover = null
			hideTimer = null
		}, 80)
	}

	function keepTip() {
		if (hideTimer) {
			clearTimeout(hideTimer)
			hideTimer = null
		}
	}
</script>

{#if hostnames.length > 0}
<div class="panel" class:alert={alerts.length > 0} style="width: {width}px;">
	<div class="name">
		{#if alerts.length > 0}
		NFS RAID ERROR: {alerts.join(", ")}
		{:else}
		disk
		{/if}
	</div>
	<div class="stack">
		{#each rows as row}
		<div class="row" class:bad={isBad(row.d)} class:warn={isWarn(row.d)} class:down={isDown(row.d)}
			on:mouseenter={(e) => showRowTip(e, row)}
			on:mouseleave={delayHide}>
			{#if row.vol}
			<div class="vol" style="width: {volWidthPct(row.vol)}%;">
				<div class="used" style="width: {usedPct(row.vol)}%;">
						{#each segments(row.vol, colorByUser) as seg (seg.id)}
					<div class="seg"
						style="width: {seg.pct}%; background: {seg.color};"
						on:mouseenter={(e) => showSegTip(e, row, seg)}
						on:mouseleave={leaveSeg}>
					</div>
					{/each}
				</div>
			</div>
			<div class="lines">
				<div class="line">{row.hostname} {raidLabel(row.d)}</div>
				<div class="line">{row.vol.label} {fmtBytes(row.vol.used)}/{fmtBytes(row.vol.total)}</div>
			</div>
			{:else}
			<div class="lines">
				<div class="line">{row.hostname} {raidLabel(row.d)}</div>
				<div class="line">no volumes</div>
			</div>
			{/if}
		</div>
		{/each}
	</div>
</div>
{/if}

{#if hover}
<div class="tipfloat"
	use:portalTip={hover.rect}
	on:mouseenter={keepTip}
	on:mouseleave={delayHide}>
	{#if hover.seg}
	<div class="tiptitle">{hover.seg.label}</div>
	<div class="tipamt">{fmtBytes(hover.seg.bytes)}</div>
	{#if hover.seg.users && hover.seg.users.length > 1}
		{#each hover.seg.users as u}
		<div class="tipuser"><span>{u.name}</span><span>{fmtBytes(u.bytes)}</span></div>
		{/each}
	{/if}
	<div class="tipsep"></div>
	{/if}
	<div class="tiptitle">{hover.hostname} health</div>
	{#if isDown(hd)}
	<div class="tipbad">unreachable (last report {fmtAgo(hd && hd.updated) || "never"})</div>
	{/if}
	<div class:tipbad={raid.ok === false} class:tipok={raid.ok === true}>
		{raid.backend || "raid"}: {raid.status || "unknown"}
	</div>
	{#each raid.arrays || [] as arr}
	<div class="tipuser">
		<span>{arr.name || "LD " + arr.id}{arr.level ? " (RAID " + arr.level + ")" : ""}</span>
		<span class:tipbad={arr.state && arr.state.toLowerCase() !== "optimal" && arr.state !== "active"}>{arr.state}</span>
	</div>
	{/each}
	{#if ctrl}
	<div class="tipuser">
		<span>controller{ctrl.model ? " " + ctrl.model : ""}</span>
		<span class:tipbad={!ctrl.ok}>{ctrl.status} {fmtTemp(ctrl.temperature)}</span>
	</div>
	{#if ctrl.backup}
	<div class="tipuser"><span>cache backup</span><span>{ctrl.backup}</span></div>
	{/if}
	{/if}
	{#if tipDisks.length}
	<div class="tipuser">
		<span>disks: {diskSummary(tipDisks)}</span>
		<span>{maxTemp(tipDisks) !== null ? "max " + fmtTemp(maxTemp(tipDisks)) : ""}</span>
	</div>
	<div class="chips">
		{#each tipDisks as disk}
		<span class="chip" class:chipbad={!disk.ok} class:chipwarn={disk.ok && disk.warnings && disk.warnings.length}
			title={diskTitle(disk)}>{disk.slot}</span>
		{/each}
	</div>
	{#each noteworthyDisks(tipDisks) as disk}
	<div class="tipnote" class:tipbad={!disk.ok}>{diskTitle(disk)}</div>
	{/each}
	{/if}
	{#each raid.warnings || [] as w}
	<div class="tipwarn">⚠ {w}</div>
	{/each}
	{#if raid.ok === false && raid.detail}
	<pre class="tipdetail">{raid.detail}</pre>
	{/if}
	{#if hd && hd.updated}
	<div class="tipamt">updated {fmtAgo(hd.updated)}</div>
	{/if}
</div>
{/if}

<style>
	.panel {
		display: flex;
		flex-direction: column;
		padding: 0px;
		background-color: #ddd;
		border-radius: 15px;
		margin: 4px;
		box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.2);
		position: relative;
		height: auto;
		box-sizing: border-box;
		color: #fff;
		overflow: visible;
	}
	.panel.alert {
		box-shadow: 0 0 12px #ff3355;
	}
	.name {
		position: absolute;
		top: 0;
		padding: 5px;
		z-index: 4;
		pointer-events: none;
	}
	.stack {
		display: flex;
		flex-direction: column;
		justify-content: flex-start;
		align-items: stretch;
		width: 100%;
		background: #000;
		padding: 1.6em 0 2px;
		box-sizing: border-box;
		border-radius: 15px;
		overflow: visible;
	}
	.row {
		position: relative;
		flex: 0 0 auto;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		width: 100%;
		min-height: 2.6em;
		padding: 0 0 2px;
		box-sizing: border-box;
	}
	.row.bad {
		outline: 2px solid #ff3355;
	}
	.row.warn {
		outline: 2px solid #ffaa33;
	}
	.row.down {
		opacity: 0.55;
	}
	.vol {
		position: relative;
		height: 2.6em;
		background: #1a1a1a;
		margin-left: 0;
		flex: 0 0 auto;
		overflow: hidden;
	}
	.lines {
		position: absolute;
		inset: 0;
		padding: 2px 8px;
		pointer-events: none;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		text-align: right;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.85);
		z-index: 2;
	}
	.line {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		line-height: 1.2em;
		font-size: 90%;
		text-align: right;
	}
	.used {
		display: flex;
		flex-direction: row;
		height: 100%;
		overflow: hidden;
	}
	.seg {
		height: 100%;
		flex: 0 0 auto;
		min-width: 0;
		box-sizing: border-box;
		border-right: 1px solid rgba(0, 0, 0, 0.25);
	}
	.seg:last-child {
		border-right: none;
	}
	.seg:hover {
		filter: brightness(1.18);
	}
	.tipfloat {
		position: fixed;
		z-index: 4000;
		background: rgba(18, 18, 18, 0.96);
		color: #fff;
		padding: 8px 12px;
		border-radius: 6px;
		min-width: 8em;
		max-width: min(280px, 80vw);
		max-height: 50vh;
		overflow-y: auto;
		font-size: 13px;
		line-height: 1.35;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
		pointer-events: auto;
	}
	.tiptitle {
		font-weight: 600;
	}
	.tipamt {
		color: #ccc;
		margin-bottom: 4px;
	}
	.tipuser {
		display: flex;
		justify-content: space-between;
		gap: 1.5em;
		white-space: nowrap;
	}
	.tipsep {
		border-top: 1px solid #444;
		margin: 6px 0;
	}
	.tipok {
		color: #7ddc8a;
	}
	.tipbad {
		color: #ff6680;
	}
	.tipwarn {
		color: #ffbb55;
	}
	.tipnote {
		font-size: 11px;
		color: #ccc;
	}
	.tipdetail {
		font-size: 10px;
		white-space: pre-wrap;
		max-height: 10em;
		overflow-y: auto;
		margin: 4px 0;
		color: #ccc;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 2px;
		margin: 3px 0;
	}
	.chip {
		min-width: 1.6em;
		text-align: center;
		font-size: 10px;
		padding: 0 2px;
		border-radius: 3px;
		background: #2e7d3a;
	}
	.chip.chipwarn {
		background: #b07a10;
	}
	.chip.chipbad {
		background: #c0233f;
	}
</style>
