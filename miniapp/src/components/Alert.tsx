import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
import s from "./Alert.module.css";

type Tone = "error" | "warning" | "info" | "success";

const ICON: Record<Tone, IconName> = {
  error: "alert-circle",
  warning: "alert-triangle",
  info: "info",
  success: "check-circle",
};

export function Alert({ tone, title, children }: { tone: Tone; title: string; children: ReactNode }) {
  return (
    <div className={`${s.alert} ${s[tone]}`} role={tone === "error" ? "alert" : "note"}>
      <Icon name={ICON[tone]} size={20} className={s.icon} />
      <div className={s.text}>
        <p className="t-detail-strong">{title}</p>
        <p className="t-description">{children}</p>
      </div>
    </div>
  );
}
