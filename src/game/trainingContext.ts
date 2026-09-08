/**
 * 训练目标上下文（叶子模块，无依赖，避免 store ↔ conversation 循环导入）。
 *
 * RoleHomeScreen 依据能力画像推荐设置当前训练目标；
 * conversation.ts 创建 CRC 会话时读取并注入患者扮演提示。
 */

let currentFocus = '';

export function setTrainingFocus(focus: string): void {
  currentFocus = (focus ?? '').trim();
}

export function getTrainingFocus(): string {
  return currentFocus;
}
