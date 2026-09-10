<script lang="ts">
  import { onMount } from "svelte";
  import { authorizeUser, getUser } from "$lib/services/api";
  import { getMaxWebApp } from "$lib/max";

  let user: any = null;
  let errorMessage = "";
  let loading = true;

  onMount(async () => {
    try {
      const webApp = getMaxWebApp();
      webApp.ready?.();
      webApp.expand?.();

      if (!localStorage.getItem("max_access_token")) {
        await authorizeUser(webApp.initData);
      }
      user = await getUser();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : "Не удалось загрузить приложение";
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head><title>MAX Mini App</title></svelte:head>

<main class="mx-auto min-h-screen max-w-md p-5">
  <section class="rounded-2xl p-5 shadow-lg tg-secondary-bg">
    <h1 class="mb-5 text-center text-2xl font-bold">MAX Mini App</h1>

    {#if loading}
      <p class="text-center tg-hint-text">Авторизация…</p>
    {:else if errorMessage}
      <p class="text-center text-red-500">{errorMessage}</p>
    {:else if user}
      <div class="space-y-3 text-center">
        {#if user.photo_url}
          <img class="mx-auto h-24 w-24 rounded-full object-cover" src={user.photo_url} alt="avatar" />
        {/if}
        <p class="text-xl font-semibold">{user.first_name || "Пользователь"} {user.last_name || ""}</p>
        {#if user.username}<p class="tg-hint-text">@{user.username}</p>{/if}
        <p class="tg-hint-text">MAX ID: {user.id}</p>
      </div>
    {/if}
  </section>
</main>
