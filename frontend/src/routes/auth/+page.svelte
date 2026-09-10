<script lang="ts">
  import { onMount } from "svelte";
  import { authorizeUser } from "../../services/api";
  import { getMaxWebApp } from "$lib/max";
  import { goto } from "$app/navigation";

  let errorMessage = "";

  onMount(async () => {
    try {
      const webApp = getMaxWebApp();
      await authorizeUser(webApp.initData);
      goto("/");
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : "Ошибка авторизации";
    }
  });
</script>

<main class="p-6 text-center">
  {#if errorMessage}
    <p class="text-red-500">{errorMessage}</p>
  {:else}
    <p class="tg-hint-text">Авторизация через MAX…</p>
  {/if}
</main>
