import type { Treatment } from '../game/types';

export const TREATMENTS: Treatment[] = [
  { id: 'aspirin', name: '阿司匹林 325mg 口服', category: 'medication' },
  { id: 'nitro', name: '硝酸甘油 舌下含服', category: 'medication' },
  { id: 'heparin', name: '肝素 静脉泵入', category: 'medication' },
  { id: 'cath-lab', name: '启动导管室', category: 'procedure' },
  { id: 'tpa', name: 'tPA（阿替普酶）', category: 'medication' },
  { id: 'epi-im', name: '肾上腺素 0.3mg 肌注', category: 'medication' },
  { id: 'antihistamine', name: '苯海拉明 静注', category: 'medication' },
  { id: 'steroids-iv', name: '甲强龙 静注', category: 'medication' },
  { id: 'neb-albuterol', name: '沙丁胺醇 雾化吸入', category: 'medication' },
  { id: 'o2', name: '吸氧', category: 'procedure' },
  { id: 'iv-fluids', name: '静脉补液（生理盐水冲击）', category: 'procedure' },
  { id: 'abx-broad', name: '广谱抗生素', category: 'medication' },
  { id: 'analgesia', name: '镇痛（吗啡）', category: 'medication' },
  { id: 'ondansetron', name: '昂丹司琼 4mg 静注', category: 'medication' },
  { id: 'surgery-consult', name: '请外科会诊', category: 'disposition' },
  { id: 'admit-icu', name: '收入 ICU', category: 'disposition' },
  { id: 'admit-floor', name: '收入普通病房', category: 'disposition' },
  { id: 'observe', name: '留观病房', category: 'disposition' },
  { id: 'discharge', name: '出院回家', category: 'disposition' },

  // Clinical-trial follow-up counseling (ct-001)
  { id: 'ct-counseling-adherence',        name: '依从性宣教与提醒策略（闹钟/家属提醒/随身药盒）', category: 'procedure' },
  { id: 'ct-counseling-safety-reporting', name: '安全报告宣教：症状/不良事件先联系研究中心',     category: 'procedure' },
  { id: 'ct-counseling-diary-accuracy',   name: '服药日记规范记录宣教（实时、如实、不补记）',    category: 'procedure' },
  { id: 'ct-counseling-conmeds',          name: '合并用药审查与预先报备宣教',                   category: 'procedure' },
  { id: 'ct-counseling-bp-measurement',   name: '家庭血压测量方法再培训',                       category: 'procedure' },
  { id: 'ct-followup-scheduled',          name: '预约下次随访并确认 24 小时联系方式',            category: 'disposition' },
];

export const treatmentById = (id: string) => TREATMENTS.find((t) => t.id === id);
