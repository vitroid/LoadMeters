import { writable } from 'svelte/store';
export let uptimes=writable({})
export let oscolors=writable({})
export let cwidth=writable({})
export let cheight=writable({})

const BASEURL = "http://" + location.hostname + ":8081"



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
            // let u = JSON.parse(result)
            let u = result
            // 計算力を計算する。
            let maxc = 0;
            for(let hostname in u){
                const c=u[hostname].cores*u[hostname].mips
                if ( maxc < c ){
                    maxc = c;
                }
            }
            // 相対計算力を格納する。
            for(let hostname in u){
                const c=u[hostname].cores*u[hostname].mips
                u[hostname].relc = c/maxc
            }
            uptimes.set(u)
            let c={}
            for(let hostname in u){
                let os=u[hostname].ostype
                if ( ! (os in c) ){
                    c[os] = palettes[Object.keys(c).length]
                }
            }
            oscolors.set(c)
        })
        return true;
    }
    catch(err){
        return false;
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

function palette(n){
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
