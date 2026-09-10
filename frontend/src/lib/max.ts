export type MaxWebApp = {
  initData: string;
  initDataUnsafe?: {
    user?: {
      id: number;
      username?: string;
      first_name?: string;
      last_name?: string;
    };
  };
  ready?: () => void;
  expand?: () => void;
  close?: () => void;
};

declare global {
  interface Window {
    WebApp?: MaxWebApp;
  }
}

export function getMaxWebApp(): MaxWebApp {
  const webApp = window.WebApp;
  if (!webApp?.initData) {
    throw new Error("Откройте приложение из MAX");
  }
  return webApp;
}
