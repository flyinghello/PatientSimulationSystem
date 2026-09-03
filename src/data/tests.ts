import type { Test } from '../game/types';
import type { ClinicId } from '../game/clinic';

export const TESTS: Test[] = [
  // ───────── Bedside ─────────
  // Trial-document checks (clinical-trial follow-up cases)
  { id: 'pill-count',       name: '药品清点（剩余药片核对）',   category: 'bedside', turnaroundSec: 15 },
  { id: 'medication-diary', name: '服药日记核查',              category: 'bedside', turnaroundSec: 15 },
  { id: 'home-bp-log',      name: '家庭血压记录核查',           category: 'bedside', turnaroundSec: 15 },
  { id: 'adverse-events',   name: '不良事件记录核查',           category: 'bedside', turnaroundSec: 15 },
  { id: 'concomitant-meds', name: '合并用药核查',              category: 'bedside', turnaroundSec: 15 },
  { id: 'glucose',    name: '床旁血糖',                 category: 'bedside', turnaroundSec: 15 },
  { id: 'peak-flow',  name: '峰流速',                   category: 'bedside', turnaroundSec: 15 },
  { id: 'urine-hcg',  name: '尿 β-hCG（妊娠）',          category: 'bedside', turnaroundSec: 18 },
  { id: 'ecg',        name: '心电图（12 导联）',          category: 'bedside', turnaroundSec: 20 },
  { id: 'strep-radt', name: '快速链球菌抗原',            category: 'bedside', turnaroundSec: 20 },
  { id: 'flu-swab',   name: '快速流感拭子',              category: 'bedside', turnaroundSec: 25 },
  { id: 'covid-swab', name: '快速 COVID-19 拭子',       category: 'bedside', turnaroundSec: 25 },
  { id: 'pocus',      name: '床旁超声（POCUS）',         category: 'bedside', turnaroundSec: 30 },

  // ───────── Lab — hematology / chemistry ─────────
  { id: 'abg',        name: '动脉血气',                 category: 'lab', turnaroundSec: 20 },
  { id: 'lactate',    name: '乳酸',                     category: 'lab', turnaroundSec: 25 },
  { id: 'cbc',        name: '血常规（含分类）',           category: 'lab', turnaroundSec: 30 },
  { id: 'bmp',        name: '基础代谢套餐',              category: 'lab', turnaroundSec: 30 },
  { id: 'lft',        name: '肝功能（LFT）',             category: 'lab', turnaroundSec: 35 },
  { id: 'lipase',     name: '脂肪酶',                   category: 'lab', turnaroundSec: 30 },
  { id: 'coag',       name: '凝血功能（PT/PTT/INR）',    category: 'lab', turnaroundSec: 30 },
  { id: 'bnp',        name: 'BNP',                      category: 'lab', turnaroundSec: 35 },
  { id: 'dimer',      name: 'D-二聚体',                 category: 'lab', turnaroundSec: 35 },
  { id: 'troponin',   name: '高敏肌钙蛋白',              category: 'lab', turnaroundSec: 40 },
  { id: 'tsh',        name: 'TSH',                      category: 'lab', turnaroundSec: 45 },
  { id: 'type-screen',name: '血型与抗体筛查',            category: 'lab', turnaroundSec: 45 },
  { id: 'urine',      name: '尿常规',                   category: 'lab', turnaroundSec: 25 },
  { id: 'urine-cx',   name: '尿培养',                   category: 'lab', turnaroundSec: 60 },
  { id: 'blood-cx',   name: '血培养（×2）',              category: 'lab', turnaroundSec: 75 },
  { id: 'utox',       name: '尿液毒理筛查',              category: 'lab', turnaroundSec: 40 },

  // ───────── Lab — endocrine / metabolic ─────────
  { id: 'hba1c',      name: '糖化血红蛋白',              category: 'lab', turnaroundSec: 45 },
  { id: 'lipid',      name: '血脂套餐',                 category: 'lab', turnaroundSec: 45 },
  { id: 'vit-d',      name: '维生素 D（25-OH）',         category: 'lab', turnaroundSec: 50 },
  { id: 'b12',        name: '维生素 B12 / 叶酸',         category: 'lab', turnaroundSec: 50 },
  { id: 'iron',       name: '铁代谢（Fe/TIBC/铁蛋白）',   category: 'lab', turnaroundSec: 50 },
  { id: 'ferritin',   name: '铁蛋白',                   category: 'lab', turnaroundSec: 45 },
  { id: 'free-t4',    name: '游离 T4 / 游离 T3',         category: 'lab', turnaroundSec: 50 },
  { id: 'cortisol',   name: '晨间皮质醇',                category: 'lab', turnaroundSec: 60 },
  { id: 'beta-hcg-q', name: 'β-hCG（定量血清）',         category: 'lab', turnaroundSec: 35 },
  { id: 'psa',        name: 'PSA',                      category: 'lab', turnaroundSec: 50 },

  // ───────── Lab — inflammation / infection ─────────
  { id: 'crp',        name: 'CRP',                      category: 'lab', turnaroundSec: 30 },
  { id: 'esr',        name: 'ESR',                      category: 'lab', turnaroundSec: 30 },
  { id: 'procal',     name: '降钙素原',                 category: 'lab', turnaroundSec: 40 },
  { id: 'hiv',        name: 'HIV 四代抗原/抗体',         category: 'lab', turnaroundSec: 70 },
  { id: 'hep-b',      name: '乙肝血清学',                category: 'lab', turnaroundSec: 75 },
  { id: 'hep-c',      name: '丙肝抗体',                 category: 'lab', turnaroundSec: 75 },
  { id: 'rpr',        name: 'RPR / VDRL（梅毒）',        category: 'lab', turnaroundSec: 60 },

  // ───────── Lab — autoimmune (rheumatology) ─────────
  { id: 'ana',        name: 'ANA',                      category: 'lab', turnaroundSec: 80 },
  { id: 'rf',         name: '类风湿因子',               category: 'lab', turnaroundSec: 70 },
  { id: 'anti-ccp',   name: '抗 CCP 抗体',              category: 'lab', turnaroundSec: 80 },
  { id: 'dsdna',      name: '抗 dsDNA 抗体',            category: 'lab', turnaroundSec: 80 },
  { id: 'c3-c4',      name: '补体 C3 / C4',             category: 'lab', turnaroundSec: 70 },

  // ───────── Lab — stool ─────────
  { id: 'stool-cx',   name: '粪便培养',                 category: 'lab', turnaroundSec: 70 },
  { id: 'fobt',       name: '粪便潜血',                 category: 'lab', turnaroundSec: 30 },
  { id: 'calpro',     name: '粪便钙卫蛋白',              category: 'lab', turnaroundSec: 60 },
  { id: 'h-pylori',   name: '幽门螺杆菌粪便抗原',         category: 'lab', turnaroundSec: 55 },

  // ───────── Lab — psych drug levels ─────────
  { id: 'lithium',    name: '锂血药浓度',               category: 'lab', turnaroundSec: 45 },
  { id: 'valproate',  name: '丙戊酸血药浓度',            category: 'lab', turnaroundSec: 45 },

  // ───────── Imaging — X-ray ─────────
  { id: 'cxr',        name: '胸部 X 线',                category: 'imaging', turnaroundSec: 40 },
  { id: 'kub',        name: '腹部 X 线（KUB）',          category: 'imaging', turnaroundSec: 40 },
  { id: 'xr-extrem',  name: '四肢 X 线',                category: 'imaging', turnaroundSec: 35 },
  { id: 'xr-spine',   name: '脊柱 X 线',                category: 'imaging', turnaroundSec: 40 },
  { id: 'xr-pelvis',  name: '骨盆 X 线',                category: 'imaging', turnaroundSec: 40 },

  // ───────── Imaging — Ultrasound / Echo ─────────
  { id: 'us-abdomen', name: '腹部超声',                 category: 'imaging', turnaroundSec: 50 },
  { id: 'us-pelvis',  name: '盆腔超声',                 category: 'imaging', turnaroundSec: 50 },
  { id: 'echo',       name: '心脏超声（TTE）',           category: 'imaging', turnaroundSec: 70 },

  // ───────── Imaging — CT ─────────
  { id: 'ct-head',    name: '头颅 CT（平扫）',           category: 'imaging', turnaroundSec: 60 },
  { id: 'ct-chest',   name: '胸部 CT',                  category: 'imaging', turnaroundSec: 65 },
  { id: 'ct-angio',   name: 'CT 血管造影（胸部，肺栓塞）', category: 'imaging', turnaroundSec: 70 },
  { id: 'ct-abdomen', name: '腹部/盆腔 CT',              category: 'imaging', turnaroundSec: 75 },
  { id: 'ct-cspine',  name: '颈椎 CT',                  category: 'imaging', turnaroundSec: 60 },

  // ───────── Imaging — MRI ─────────
  { id: 'mri-brain',  name: '脑部 MRI',                 category: 'imaging', turnaroundSec: 120 },
  { id: 'mri-cspine', name: '颈椎 MRI',                 category: 'imaging', turnaroundSec: 110 },
  { id: 'mri-lspine', name: '腰椎 MRI',                 category: 'imaging', turnaroundSec: 110 },
  { id: 'mri-abd',    name: '腹部 MRI（MRCP）',          category: 'imaging', turnaroundSec: 130 },

  // ───────── Imaging / functional — specialty ─────────
  { id: 'dexa',       name: 'DEXA 骨密度',              category: 'imaging', turnaroundSec: 70 },
  { id: 'mammogram',  name: '乳腺钼靶',                 category: 'imaging', turnaroundSec: 65 },
  { id: 'oct',        name: 'OCT（视网膜）',            category: 'imaging', turnaroundSec: 50 },
  { id: 'visual-field', name: '视野检查',               category: 'imaging', turnaroundSec: 55 },
  { id: 'fundoscopy', name: '散瞳眼底检查',              category: 'bedside', turnaroundSec: 30 },
  { id: 'audiometry', name: '听力学检查',               category: 'bedside', turnaroundSec: 35 },
  { id: 'eeg',        name: '脑电图',                   category: 'bedside', turnaroundSec: 90 },
  { id: 'emg-ncs',    name: '肌电图 / 神经传导',         category: 'bedside', turnaroundSec: 80 },
  { id: 'spirometry', name: '肺功能（PFT）',            category: 'bedside', turnaroundSec: 50 },
  { id: 'pap-smear',  name: '宫颈刮片 / HPV 联合筛查',    category: 'bedside', turnaroundSec: 60 },
  { id: 'skin-biopsy',name: '皮肤活检',                 category: 'bedside', turnaroundSec: 90 },
];

export const testById = (id: string) => TESTS.find((t) => t.id === id);

// Convenience panels — fire several tests with one click.
//
// `clinicIds` scopes a panel to the polyclinic view. ED panels omit it and
// therefore only appear in the ER flow (`PatientPanel.tsx`). Polyclinic
// panels list every specialty they apply to; the polyclinic view filters
// `TEST_PANELS` by the current clinic.
export interface TestPanel {
  id: string;
  label: string;
  description: string;
  testIds: string[];
  clinicIds?: ClinicId[];
}

export const TEST_PANELS: TestPanel[] = [
  // ───────── ED panels (no clinicIds → ER-only) ─────────
  {
    id: 'routine-labs',
    label: '常规化验',
    description: '血常规、基础代谢、凝血',
    testIds: ['cbc', 'bmp', 'coag'],
  },
  {
    id: 'chest-pain',
    label: '胸痛检查组合',
    description: '心电图、肌钙蛋白、胸片、D-二聚体、基础代谢、血常规',
    testIds: ['ecg', 'troponin', 'cxr', 'dimer', 'bmp', 'cbc'],
  },
  {
    id: 'sepsis',
    label: '脓毒症检查组合',
    description: '血常规、基础代谢、乳酸、血培养、尿常规、尿培养',
    testIds: ['cbc', 'bmp', 'lactate', 'blood-cx', 'urine', 'urine-cx'],
  },
  {
    id: 'abdominal',
    label: '腹部检查组合',
    description: '血常规、基础代谢、肝功能、脂肪酶、尿常规、腹部超声',
    testIds: ['cbc', 'bmp', 'lft', 'lipase', 'urine', 'us-abdomen'],
  },
  {
    id: 'stroke',
    label: '卒中检查组合',
    description: '头颅 CT、心电图、血常规、基础代谢、凝血、血糖',
    testIds: ['ct-head', 'ecg', 'cbc', 'bmp', 'coag', 'glucose'],
  },
  {
    id: 'trauma',
    label: '创伤组合',
    description: '血常规、基础代谢、凝血、血型筛查、乳酸、胸片、骨盆',
    testIds: ['cbc', 'bmp', 'coag', 'type-screen', 'lactate', 'cxr', 'xr-pelvis'],
  },

  // ───────── Polyclinic — shared across multiple specialties ─────────
  {
    id: 'basic-metabolic-workup',
    label: '基础代谢检查',
    description: '血常规、基础代谢、TSH',
    testIds: ['cbc', 'bmp', 'tsh'],
    clinicIds: ['internal-medicine', 'endocrinology', 'nephrology', 'hematology', 'psychiatry', 'pediatrics'],
  },
  {
    id: 'general-screening-labs',
    label: '常规筛查化验',
    description: '血常规、基础代谢、肝功能、TSH、尿常规',
    testIds: ['cbc', 'bmp', 'lft', 'tsh', 'urine'],
    clinicIds: ['internal-medicine', 'endocrinology', 'rheumatology'],
  },
  {
    id: 'uti-workup',
    label: '尿路感染检查',
    description: '尿常规、尿培养',
    testIds: ['urine', 'urine-cx'],
    clinicIds: ['internal-medicine', 'urology', 'nephrology', 'obgyn', 'infectious-disease', 'pediatrics'],
  },
  {
    id: 'preop-clearance',
    label: '术前评估',
    description: '血常规、基础代谢、凝血、血型筛查、心电图、胸片',
    testIds: ['cbc', 'bmp', 'coag', 'type-screen', 'ecg', 'cxr'],
    clinicIds: ['general-surgery', 'orthopedics', 'urology', 'obgyn', 'cardiology'],
  },

  // ───────── Internal Medicine ─────────
  {
    id: 'im-annual-physical',
    label: '年度体检化验',
    description: '血常规、基础代谢、肝功能、脂肪酶、TSH、尿常规',
    testIds: ['cbc', 'bmp', 'lft', 'lipase', 'tsh', 'urine'],
    clinicIds: ['internal-medicine'],
  },
  {
    id: 'im-fatigue-workup',
    label: '乏力检查',
    description: '血常规、基础代谢、TSH、肝功能、血糖',
    testIds: ['cbc', 'bmp', 'tsh', 'lft', 'glucose'],
    clinicIds: ['internal-medicine'],
  },

  // ───────── Cardiology ─────────
  {
    id: 'cards-new-patient',
    label: '心内科新患者',
    description: '心电图、BNP、肌钙蛋白、基础代谢、血常规',
    testIds: ['ecg', 'bnp', 'troponin', 'bmp', 'cbc'],
    clinicIds: ['cardiology'],
  },
  {
    id: 'cards-heart-failure',
    label: '心力衰竭检查',
    description: 'BNP、心脏超声、心电图、基础代谢、胸片',
    testIds: ['bnp', 'echo', 'ecg', 'bmp', 'cxr'],
    clinicIds: ['cardiology'],
  },
  {
    id: 'cards-chest-pain-outpt',
    label: '门诊胸痛',
    description: '心电图、肌钙蛋白、胸片、心脏超声',
    testIds: ['ecg', 'troponin', 'cxr', 'echo'],
    clinicIds: ['cardiology', 'internal-medicine'],
  },

  // ───────── Neurology ─────────
  {
    id: 'neuro-headache-workup',
    label: '头痛检查',
    description: '脑部 MRI、血常规、基础代谢',
    testIds: ['mri-brain', 'cbc', 'bmp'],
    clinicIds: ['neurology'],
  },
  {
    id: 'neuro-back-pain',
    label: '腰背痛 / 神经根病',
    description: '腰椎 MRI、脊柱 X 线',
    testIds: ['mri-lspine', 'xr-spine'],
    clinicIds: ['neurology', 'orthopedics'],
  },
  {
    id: 'neuro-neck-pain',
    label: '颈痛 / 颈椎检查',
    description: '颈椎 MRI、脊柱 X 线',
    testIds: ['mri-cspine', 'xr-spine'],
    clinicIds: ['neurology', 'orthopedics'],
  },

  // ───────── Dermatology ─────────
  {
    id: 'derm-systemic-rash',
    label: '系统性皮疹检查',
    description: '血常规、肝功能、基础代谢',
    testIds: ['cbc', 'lft', 'bmp'],
    clinicIds: ['dermatology'],
  },

  // ───────── Endocrinology ─────────
  {
    id: 'endo-diabetes-followup',
    label: '糖尿病随访',
    description: '血糖、基础代谢、尿常规',
    testIds: ['glucose', 'bmp', 'urine'],
    clinicIds: ['endocrinology', 'internal-medicine'],
  },
  {
    id: 'endo-thyroid-workup',
    label: '甲状腺检查',
    description: 'TSH、血常规、基础代谢',
    testIds: ['tsh', 'cbc', 'bmp'],
    clinicIds: ['endocrinology'],
  },

  // ───────── Gastroenterology ─────────
  {
    id: 'gi-abdominal-workup',
    label: '腹部检查',
    description: '血常规、基础代谢、肝功能、脂肪酶、腹部超声',
    testIds: ['cbc', 'bmp', 'lft', 'lipase', 'us-abdomen'],
    clinicIds: ['gastroenterology', 'general-surgery'],
  },
  {
    id: 'gi-liver-workup',
    label: '肝脏检查',
    description: '肝功能、凝血、血常规、腹部超声、MRCP',
    testIds: ['lft', 'coag', 'cbc', 'us-abdomen', 'mri-abd'],
    clinicIds: ['gastroenterology'],
  },

  // ───────── Pulmonology ─────────
  {
    id: 'pulm-dyspnea-workup',
    label: '呼吸困难检查',
    description: '胸片、峰流速、动脉血气、BNP、血常规',
    testIds: ['cxr', 'peak-flow', 'abg', 'bnp', 'cbc'],
    clinicIds: ['pulmonology'],
  },
  {
    id: 'pulm-chronic-cough',
    label: '慢性咳嗽检查',
    description: '胸片、胸部 CT、血常规、峰流速',
    testIds: ['cxr', 'ct-chest', 'cbc', 'peak-flow'],
    clinicIds: ['pulmonology'],
  },

  // ───────── Nephrology ─────────
  {
    id: 'neph-renal-workup',
    label: '肾脏检查',
    description: '基础代谢、血常规、尿常规、腹部超声',
    testIds: ['bmp', 'cbc', 'urine', 'us-abdomen'],
    clinicIds: ['nephrology'],
  },
  {
    id: 'neph-stone-workup',
    label: '肾结石检查',
    description: '基础代谢、尿常规、KUB、腹部 CT',
    testIds: ['bmp', 'urine', 'kub', 'ct-abdomen'],
    clinicIds: ['nephrology', 'urology'],
  },

  // ───────── Rheumatology ─────────
  {
    id: 'rheum-joint-workup',
    label: '关节 / 关节炎检查',
    description: '血常规、基础代谢、肝功能、尿常规、四肢 X 线',
    testIds: ['cbc', 'bmp', 'lft', 'urine', 'xr-extrem'],
    clinicIds: ['rheumatology'],
  },
  {
    id: 'rheum-systemic-workup',
    label: '系统性疾病检查',
    description: '血常规、基础代谢、肝功能、尿常规、胸片',
    testIds: ['cbc', 'bmp', 'lft', 'urine', 'cxr'],
    clinicIds: ['rheumatology'],
  },

  // ───────── Hematology ─────────
  {
    id: 'heme-anemia-workup',
    label: '贫血检查',
    description: '血常规、基础代谢、肝功能',
    testIds: ['cbc', 'bmp', 'lft'],
    clinicIds: ['hematology'],
  },
  {
    id: 'heme-coag-workup',
    label: '凝血功能障碍检查',
    description: '血常规、凝血、肝功能、血型筛查',
    testIds: ['cbc', 'coag', 'lft', 'type-screen'],
    clinicIds: ['hematology'],
  },

  // ───────── Infectious Disease ─────────
  {
    id: 'id-fever-workup',
    label: '发热检查',
    description: '血常规、基础代谢、肝功能、血培养、尿常规、尿培养、胸片',
    testIds: ['cbc', 'bmp', 'lft', 'blood-cx', 'urine', 'urine-cx', 'cxr'],
    clinicIds: ['infectious-disease'],
  },
  {
    id: 'id-respiratory-viral',
    label: '呼吸道病毒组合',
    description: '流感拭子、COVID 拭子、链球菌快速检测、胸片',
    testIds: ['flu-swab', 'covid-swab', 'strep-radt', 'cxr'],
    clinicIds: ['infectious-disease', 'internal-medicine', 'pediatrics'],
  },

  // ───────── Allergy / Immunology ─────────
  {
    id: 'allergy-baseline',
    label: '过敏基线化验',
    description: '血常规、峰流速',
    testIds: ['cbc', 'peak-flow'],
    clinicIds: ['allergy-immunology'],
  },

  // ───────── Psychiatry ─────────
  {
    id: 'psych-med-baseline',
    label: '精神科用药基线',
    description: '血常规、基础代谢、TSH、肝功能',
    testIds: ['cbc', 'bmp', 'tsh', 'lft'],
    clinicIds: ['psychiatry'],
  },
  {
    id: 'psych-altered-mental',
    label: '意识障碍',
    description: '基础代谢、TSH、血糖、尿毒理',
    testIds: ['bmp', 'tsh', 'glucose', 'utox'],
    clinicIds: ['psychiatry'],
  },

  // ───────── OB/GYN ─────────
  {
    id: 'obgyn-pregnancy-workup',
    label: '妊娠检查',
    description: '尿 β-hCG、血常规、基础代谢、盆腔超声',
    testIds: ['urine-hcg', 'cbc', 'bmp', 'us-pelvis'],
    clinicIds: ['obgyn'],
  },
  {
    id: 'obgyn-pelvic-pain',
    label: '盆腔痛检查',
    description: '尿 β-hCG、尿常规、盆腔超声、血常规',
    testIds: ['urine-hcg', 'urine', 'us-pelvis', 'cbc'],
    clinicIds: ['obgyn'],
  },

  // ───────── Urology ─────────
  {
    id: 'uro-hematuria-workup',
    label: '血尿检查',
    description: '尿常规、尿培养、基础代谢、腹部 CT',
    testIds: ['urine', 'urine-cx', 'bmp', 'ct-abdomen'],
    clinicIds: ['urology'],
  },
  {
    id: 'uro-prostate-workup',
    label: '前列腺 / 下尿路症状检查',
    description: '尿常规、基础代谢、血常规',
    testIds: ['urine', 'bmp', 'cbc'],
    clinicIds: ['urology'],
  },

  // ───────── Ophthalmology ─────────
  {
    id: 'ophth-vision-workup',
    label: '视力丧失检查',
    description: '血糖、基础代谢、脑部 MRI',
    testIds: ['glucose', 'bmp', 'mri-brain'],
    clinicIds: ['ophthalmology'],
  },

  // ───────── ENT ─────────
  {
    id: 'ent-sore-throat',
    label: '咽痛检查',
    description: '链球菌快速检测、流感拭子、COVID 拭子、血常规',
    testIds: ['strep-radt', 'flu-swab', 'covid-swab', 'cbc'],
    clinicIds: ['ent'],
  },
  {
    id: 'ent-neck-mass',
    label: '颈部肿块检查',
    description: '血常规、TSH、胸部 CT、腹部超声',
    testIds: ['cbc', 'tsh', 'ct-chest', 'us-abdomen'],
    clinicIds: ['ent'],
  },

  // ───────── Orthopedics ─────────
  {
    id: 'ortho-extremity-injury',
    label: '四肢损伤',
    description: '四肢 X 线、血常规',
    testIds: ['xr-extrem', 'cbc'],
    clinicIds: ['orthopedics'],
  },
  {
    id: 'ortho-joint-pain',
    label: '关节痛检查',
    description: '四肢 X 线、血常规、基础代谢',
    testIds: ['xr-extrem', 'cbc', 'bmp'],
    clinicIds: ['orthopedics'],
  },

  // ───────── Pediatrics ─────────
  {
    id: 'peds-fever',
    label: '小儿发热',
    description: '血常规、基础代谢、尿常规、链球菌快速检测、流感拭子',
    testIds: ['cbc', 'bmp', 'urine', 'strep-radt', 'flu-swab'],
    clinicIds: ['pediatrics'],
  },
  {
    id: 'peds-wheeze',
    label: '小儿喘息',
    description: '峰流速、胸片、COVID 拭子、流感拭子',
    testIds: ['peak-flow', 'cxr', 'covid-swab', 'flu-swab'],
    clinicIds: ['pediatrics'],
  },

  // ───────── General Surgery ─────────
  {
    id: 'surg-rlq-workup',
    label: '右下腹 / 阑尾炎检查',
    description: '血常规、基础代谢、尿常规、尿 β-hCG、腹部 CT',
    testIds: ['cbc', 'bmp', 'urine', 'urine-hcg', 'ct-abdomen'],
    clinicIds: ['general-surgery'],
  },
  {
    id: 'surg-hernia-workup',
    label: '疝 / 肿块检查',
    description: '血常规、基础代谢、腹部超声',
    testIds: ['cbc', 'bmp', 'us-abdomen'],
    clinicIds: ['general-surgery'],
  },
];
