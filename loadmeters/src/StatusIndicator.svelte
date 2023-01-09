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
        width:400px;
        height:400px;
        margin-left:-200px;
        margin-top:-200px;
        z-index: 10;
        font-size: 500%;
        color: #fff;
    }
</style>
