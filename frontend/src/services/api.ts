import { goto } from "$app/navigation";

export async function authorizeUser(initData: string) {
  const res = await fetch("/api/user/auth", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ initData }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Ошибка авторизации");
  localStorage.setItem("max_access_token", data.access_token);
  return data;
}

export async function getUser() {
  const token = localStorage.getItem("max_access_token");
  if (!token) {
    goto("/auth");
    return null;
  }

  const res = await fetch("/api/user/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    localStorage.removeItem("max_access_token");
    goto("/auth");
    return null;
  }
  return res.json();
}
