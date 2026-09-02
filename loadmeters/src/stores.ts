import { writable } from 'svelte/store';
export let uptimes=writable({})
export let oscolors=writable({})
export let cwidth=writable(0)
export let cheight=writable(0)
export let panelWidth=writable(200)
export let disks=writable({})

// 同一オリジン。UI と API は同じポートで配信する。
const BASEURL = ""



let palettes = Array(100)
for(let i=0;i<100;i++){
    palettes[i] = palette(i)
}



async function fetchWithTimeout(resource, options = {}) {
    const { timeout = 8000 } = options;

    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    const response = await fetch(resource, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  }

export async function uptime(){
    try {
        const res = await fetchWithTimeout(BASEURL+'/v1/stat', {
            method: "GET",
        })
        res.json().then(result=>{
            console.log("🔍 stores.ts: Raw API response", typeof result, result)
            
            // データの妥当性チェック
            if (!result || typeof result !== 'object' || Array.isArray(result)) {
                console.error("🔍 stores.ts: Invalid API response", result)
                uptimes.set({})
                return
            }
            
            let u = result
            console.log("🔍 stores.ts: Server list", Object.keys(u))
            
            // 計算力を計算する。
            let maxc = 0;
            for(let hostname in u){
                if (!u[hostname].cores || !u[hostname].mips) {
                    console.warn("🔍 stores.ts: Missing cores/mips for", hostname, u[hostname])
                    continue;
                }
                const c=u[hostname].cores*u[hostname].mips
                if ( maxc < c ){
                    maxc = c;
                }
            }
            console.log("🔍 stores.ts: Max compute power", maxc)
            
            // 相対計算力を格納する。
            for(let hostname in u){
                if (!u[hostname].cores || !u[hostname].mips || u[hostname].cores <= 0 || u[hostname].mips <= 0) {
                    console.warn("🔍 stores.ts: Invalid cores/mips for", hostname, "cores:", u[hostname].cores, "mips:", u[hostname].mips)
                    u[hostname].relc = 0.2; // デフォルト値を0.2に設定（20%）
                    u[hostname].cores = u[hostname].cores || 1; // デフォルト値
                    u[hostname].mips = u[hostname].mips || 1000; // デフォルト値
                    continue;
                }
                const c=u[hostname].cores*u[hostname].mips
                u[hostname].relc = maxc > 0 ? c/maxc : 0.2
                console.log("🔍 stores.ts: Relative compute for", hostname, u[hostname].relc)
            }
            
            console.log("🔍 stores.ts: Setting uptimes with", Object.keys(u).length, "servers")
            uptimes.set(u)
            
            let c={}
            for(let hostname in u){
                let os=u[hostname].ostype
                if ( ! (os in c) ){
                    c[os] = palettes[Object.keys(c).length]
                }
            }
            console.log("🔍 stores.ts: OS colors", c)
            oscolors.set(c)
        }).catch(err => {
            console.error("🔍 stores.ts: JSON parsing error", err)
            uptimes.set({})
        })
        return true;
    }
    catch(err){
        console.error("🔍 stores.ts: Fetch error", err)
        uptimes.set({})
        return false;
    }
}


export async function fetchDisk(){
    try {
        const res = await fetchWithTimeout(BASEURL+'/v1/disk', {
            method: "GET",
        })
        const result = await res.json()
        if (!result || typeof result !== 'object' || Array.isArray(result)) {
            disks.set({})
            return false
        }
        disks.set(result)
        return true
    }
    catch(err){
        console.error("stores.ts: disk fetch error", err)
        return false
    }
}


export function hslToHex(h, s, l) {
    l /= 100;
    const a = s * Math.min(l, 1 - l) / 100;
    const f = n => {
        const k = (n + h / 30) % 12;
        const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
        return Math.round(255 * color).toString(16).padStart(2, '0');   // convert to Hex and prefix "0" if needed
    };
    return `#${f(0)}${f(8)}${f(4)}`;
}

export function palette(n){
    if ( n < 0 ){
        return "#444"
    }
    let tau=(Math.sqrt(5)-1)/2
    // let ra = get(huerange)
    let hue = (tau*n*360) % 360
    let s=30
    let v=50
    return hslToHex(hue, s, v)
}
