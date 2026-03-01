<script>
    export let online;
</script>

<div>
    {#if !online}
    OFFLINE
    {/if}
</div>

<style>
    div {
        position: absolute;
        top: 50%;
        left: 50%;
        z-index: 100;
        font-size: 500%;
        color: #fff;
    }
</style>
