/**
 * Medication catalog for the polyclinic prescription workflow.
 *
 * Each entry lists the diagnosis IDs (from `polyclinicPatients.ts` /
 * `patients.ts`) for which the drug is clinically appropriate, plus an
 * explicit contraindications list when the drug would be dangerous or
 * medically inappropriate.  Grading uses these lists to award bonuses for
 * correct prescribing and penalties for wrong/dangerous choices.
 *
 * This is a TRAINING catalogue — doses and indications reflect common
 * real-world outpatient practice but must NOT be used as clinical guidance
 * outside the simulator.
 */

import type { ClinicId } from '../game/clinic';

/**
 * High-level therapeutic category used to group the prescription pad.
 * Finer-grained `class` (e.g. "SSRI", "ACE inhibitor") nests under this.
 */
export type MedicationCategory =
  | 'antibiotic'
  | 'antiviral'
  | 'antifungal'
  | 'cardiovascular'
  | 'antiplatelet-anticoagulant'
  | 'lipid-lowering'
  | 'endocrine'
  | 'analgesic'
  | 'gastrointestinal'
  | 'respiratory'
  | 'allergy'
  | 'neurology'
  | 'psychiatry'
  | 'rheumatology'
  | 'dermatology'
  | 'ophthalmic'
  | 'urology'
  | 'obgyn'
  | 'hematology-nutrition';

export interface Medication {
  id: string;
  name: string;
  form:
    | '片剂'
    | '胶囊'
    | '注射剂'
    | '溶液'
    | '喷雾剂'
    | '外用制剂'
    | 'capsule'
    | 'solution'
    | 'cream'
    | 'spray'
    | 'injection';
  category: MedicationCategory;
  class: string;
  defaultDose: string;
  defaultDuration: string;
  /** Diagnosis IDs for which this drug is an appropriate outpatient choice. */
  indications: string[];
  /** Diagnosis IDs where this drug is explicitly wrong / dangerous. */
  contraindications?: string[];
}

/* ------------------------------------------------------------------ */
/*  Catalog                                                            */
/* ------------------------------------------------------------------ */

export const MEDICATIONS: Medication[] = [
  // ─────────── Antibiotics ───────────
  {
    id: 'amoxicillin-clavulanate-1g',
    name: '阿莫西林/克拉维酸 1g',
    form: '片剂',
    category: 'antibiotic',
    class: '青霉素 + β-内酰胺酶抑制剂',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '7 days',
    indications: [
      'acute-sinusitis-bacterial',
      'otitis-media-adult',
      'acute-otitis-media-child',
      'community-acquired-pna',
      'pneumonia',
      'cellulitis-non-limb-threatening',
      'dental-abscess',
      'pid-outpatient',
    ],
    contraindications: ['drug-allergy-penicillin', 'viral-uri', 'viral-gastroenteritis'],
  },
  {
    id: 'azithromycin-500',
    name: '阿奇霉素 500mg',
    form: '片剂',
    category: 'antibiotic',
    class: '大环内酯类抗生素',
    defaultDose: '1 tab, 1×1, PO (day 1: 2 tb)',
    defaultDuration: '5 days',
    indications: [
      'community-acquired-pna',
      'pneumonia',
      'chronic-bronchitis',
      'pid-outpatient',
      'pid-gonococcal',
    ],
    contraindications: ['viral-uri'],
  },
  {
    id: 'ciprofloxacin-500',
    name: '环丙沙星 500mg',
    form: '片剂',
    category: 'antibiotic',
    class: '氟喹诺酮类抗生素',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '7 days',
    indications: [
      'uti-uncomplicated',
      'recurrent-uti-female',
      'uti',
      'pyelonephritis',
      'prostatitis-chronic',
      'brucellosis',
    ],
    contraindications: ['viral-uri', 'viral-gastroenteritis', 'atopic-dermatitis'],
  },
  {
    id: 'cefuroxime-500',
    name: '头孢呋辛酯 500mg',
    form: '片剂',
    category: 'antibiotic',
    class: '第二代头孢菌素',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '7 days',
    indications: [
      'acute-sinusitis-bacterial',
      'otitis-media-adult',
      'community-acquired-pna',
      'cellulitis-non-limb-threatening',
    ],
  },
  {
    id: 'doxycycline-100',
    name: '多西环素 100mg',
    form: '片剂',
    category: 'antibiotic',
    class: '四环素类抗生素',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '14 days',
    indications: [
      'acne-vulgaris',
      'rosacea',
      'lyme-disease',
      'brucellosis',
      'pid-outpatient',
      'chronic-bronchitis',
      'community-acquired-pna',
    ],
    contraindications: ['normal-pregnancy-2nd-tri', 'gestational-dm'],
  },
  {
    id: 'penicillin-v-500',
    name: '青霉素 V 500mg',
    form: '片剂',
    category: 'antibiotic',
    class: '天然青霉素',
    defaultDose: '1 tab,4×1, PO',
    defaultDuration: '10 days',
    indications: ['tonsillitis-strep', 'strep-pharyngitis-child'],
    contraindications: ['drug-allergy-penicillin', 'viral-uri'],
  },
  {
    id: 'metronidazole-500',
    name: '甲硝唑 500mg',
    form: '片剂',
    category: 'antibiotic',
    class: '硝基咪唑类抗生素',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '7 days',
    indications: ['bacterial-vaginosis', 'pid-outpatient', 'trichomoniasis'],
    contraindications: ['alcohol-use-disorder'],
  },
  {
    id: 'nitrofurantoin-100',
    name: '呋喃妥因 100mg',
    form: '胶囊',
    category: 'antibiotic',
    class: '泌尿系统抗生素',
    defaultDose: '1 cap, 2×1, PO',
    defaultDuration: '5 days',
    indications: ['uti-uncomplicated', 'recurrent-uti-female', 'uti'],
    contraindications: ['ckd-stage3a', 'pyelonephritis', 'diabetic-nephropathy'],
  },
  {
    id: 'tmp-smx-ds',
    name: '甲氧苄啶/磺胺甲噁唑（复方）',
    form: '片剂',
    category: 'antibiotic',
    class: '叶酸拮抗抗生素',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '5 days',
    indications: ['uti-uncomplicated', 'recurrent-uti-female', 'prostatitis-chronic'],
    contraindications: ['ckd-stage3a', 'normal-pregnancy-2nd-tri'],
  },
  {
    id: 'clotrimazole-vag',
    name: '克霉唑阴道乳膏',
    form: '外用制剂',
    category: 'antifungal',
    class: '外用唑类抗真菌药',
    defaultDose: '1 applicator at bedtime',
    defaultDuration: '7 days',
    indications: ['candida-vulvovaginitis'],
  },
  {
    id: 'acyclovir-800',
    name: '阿昔洛韦 800mg',
    form: '片剂',
    category: 'antiviral',
    class: '抗病毒药（核苷类似物）',
    defaultDose: '1 tab,5×1, PO',
    defaultDuration: '7 days',
    indications: ['shingles', 'herpes-simplex-keratitis', 'varicella'],
  },

  // ─────────── Antihypertensives ───────────
  {
    id: 'amlodipine-5',
    name: '氨氯地平 5mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '钙通道阻滞剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'essential-hypertension',
      'htn-uncontrolled',
      'hypertensive-nephrosclerosis',
      'stable-angina',
      'renal-artery-stenosis',
    ],
    contraindications: ['orthostatic-hypotension', 'chf-nyha2'],
  },
  {
    id: 'ramipril-5',
    name: '雷米普利 5mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '血管紧张素转换酶抑制药 (ACEI)',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'essential-hypertension',
      'htn-uncontrolled',
      'chf-nyha2',
      'chf',
      'diabetic-nephropathy',
      'iga-nephropathy',
      'ckd-stage3a',
      'type2-diabetes',
      'type2-dm-uncontrolled',
      'hypertensive-nephrosclerosis',
    ],
    contraindications: [
      'hereditary-angioedema',
      'angioedema-ace',
      'renal-artery-stenosis',
      'normal-pregnancy-2nd-tri',
      'aki-pre-renal',
    ],
  },
  {
    id: 'losartan-50',
    name: '氯沙坦 50mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '血管紧张素受体阻滞药 (ARB)',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'essential-hypertension',
      'htn-uncontrolled',
      'diabetic-nephropathy',
      'chf-nyha2',
      'hypertensive-nephrosclerosis',
    ],
    contraindications: ['normal-pregnancy-2nd-tri', 'aki-pre-renal'],
  },
  {
    id: 'metoprolol-50',
    name: '琥珀酸美托洛尔 50mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '心脏选择性 β-受体阻滞剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'paroxysmal-afib',
      'stable-angina',
      'chf-nyha2',
      'chf',
      'ventricular-pvcs',
      'hcm',
      'essential-hypertension',
      'htn-uncontrolled',
    ],
    contraindications: ['asthma-chronic', 'asthma-allergic', 'copd-gold2'],
  },
  {
    id: 'bisoprolol-5',
    name: '比索洛尔 5mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '心脏选择性 β-受体阻滞剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'chf-nyha2',
      'chf',
      'paroxysmal-afib',
      'stable-angina',
      'essential-hypertension',
    ],
    contraindications: ['asthma-chronic', 'asthma-allergic'],
  },
  {
    id: 'hctz-25',
    name: '氢氯噻嗪 25mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '噻嗪类利尿药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['essential-hypertension', 'htn-uncontrolled'],
    contraindications: ['gout', 'nephrolithiasis-recurrent'],
  },
  {
    id: 'indapamide-15',
    name: '吲达帕胺缓释 1.5mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '类噻嗪利尿药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['essential-hypertension', 'htn-uncontrolled'],
    contraindications: ['gout'],
  },
  {
    id: 'spironolactone-25',
    name: '螺内酯 25mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '醛固酮拮抗药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['chf-nyha2', 'chf', 'htn-uncontrolled', 'pcos', 'pcos-obgyn'],
    contraindications: ['ckd-stage3a', 'aki-pre-renal'],
  },

  // ─────────── Antidiabetics ───────────
  {
    id: 'metformin-500',
    name: '二甲双胍 500mg',
    form: '片剂',
    category: 'endocrine',
    class: '双胍类',
    defaultDose: '1 tab, 2×1, PO (with food)',
    defaultDuration: 'ongoing',
    indications: [
      'type2-diabetes',
      'type2-dm-uncontrolled',
      'pcos',
      'pcos-obgyn',
      'gestational-dm',
    ],
    contraindications: ['ckd-stage3a', 'aki-pre-renal', 'type1-dm-new'],
  },
  {
    id: 'gliclazide-30',
    name: '格列齐特缓释 30mg',
    form: '片剂',
    category: 'endocrine',
    class: '磺脲类',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['type2-diabetes', 'type2-dm-uncontrolled'],
    contraindications: ['type1-dm-new', 'hypoglycemia'],
  },
  {
    id: 'empagliflozin-10',
    name: '恩格列净 10mg',
    form: '片剂',
    category: 'endocrine',
    class: 'SGLT2 抑制剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'type2-diabetes',
      'type2-dm-uncontrolled',
      'chf-nyha2',
      'chf',
      'diabetic-nephropathy',
    ],
    contraindications: ['type1-dm-new', 'aki-pre-renal'],
  },
  {
    id: 'insulin-glargine',
    name: '甘精胰岛素（基础）',
    form: '注射剂',
    category: 'endocrine',
    class: '长效基础胰岛素',
    defaultDose: '10 IU at night SC',
    defaultDuration: 'ongoing',
    indications: [
      'type1-dm-new',
      'type2-dm-uncontrolled',
      'gestational-dm',
      'diabetic-nephropathy',
    ],
  },
  {
    id: 'insulin-aspart',
    name: '门冬胰岛素（餐时）',
    form: '注射剂',
    category: 'endocrine',
    class: '速效餐时胰岛素',
    defaultDose: '4-6 IU before meal SC',
    defaultDuration: 'ongoing',
    indications: ['type1-dm-new', 'type2-dm-uncontrolled'],
  },

  // ─────────── Analgesics / NSAIDs ───────────
  {
    id: 'paracetamol-500',
    name: '对乙酰氨基酚 500mg',
    form: '片剂',
    category: 'analgesic',
    class: '解热镇痛药',
    defaultDose: '1-2 tb, 3×1, PO',
    defaultDuration: '5 days',
    indications: [
      'tension-headache',
      'migraine-without-aura',
      'osteoarthritis-knee',
      'osteoarthritis-hand',
      'hip-oa-moderate',
      'viral-uri',
      'viral-gastroenteritis',
      'febrile-seizure',
      'hand-foot-mouth',
      'varicella',
      'influenza',
      'plantar-fasciitis',
      'lateral-epicondylitis',
      'frozen-shoulder',
      'tmj-dysfunction',
    ],
    contraindications: ['chronic-hepatitis-b', 'chronic-hepatitis-c', 'alcoholic-hepatitis'],
  },
  {
    id: 'ibuprofen-400',
    name: '布洛芬 400mg',
    form: '片剂',
    category: 'analgesic',
    class: '非甾体抗炎药 (NSAID)',
    defaultDose: '1 tab, 3×1, PO',
    defaultDuration: '5 days',
    indications: [
      'tension-headache',
      'migraine-without-aura',
      'osteoarthritis-knee',
      'hip-oa-moderate',
      'lateral-epicondylitis',
      'plantar-fasciitis',
      'achilles-tendinopathy',
      'ankle-sprain-gr2',
      'subacromial-bursitis',
      'menorrhagia-fibroids',
      'pericarditis',
      'gout',
    ],
    contraindications: [
      'peptic-ulcer-disease',
      'ckd-stage3a',
      'chf-nyha2',
      'gerd',
      'aki-pre-renal',
      'asthma-allergic',
    ],
  },
  {
    id: 'naproxen-500',
    name: '萘普生 500mg',
    form: '片剂',
    category: 'analgesic',
    class: '非甾体抗炎药 (NSAID)',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '10 days',
    indications: [
      'gout',
      'ankylosing-spondylitis',
      'rheumatoid-arthritis-early',
      'osteoarthritis-knee',
      'hip-oa-moderate',
      'migraine-without-aura',
      'meniscal-tear',
      'pericarditis',
    ],
    contraindications: ['peptic-ulcer-disease', 'ckd-stage3a', 'chf-nyha2', 'gerd'],
  },
  {
    id: 'diclofenac-75',
    name: '双氯芬酸 75mg',
    form: '片剂',
    category: 'analgesic',
    class: '非甾体抗炎药 (NSAID)',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '7 days',
    indications: [
      'kidney-stone-5mm',
      'nephrolithiasis-recurrent',
      'kidney-stone',
      'gallstones-biliary-colic',
      'gallstones-cholelithiasis',
      'lumbar-disc-herniation',
      'sciatica-l5',
      'gout',
    ],
    contraindications: ['peptic-ulcer-disease', 'ckd-stage3a'],
  },
  {
    id: 'tramadol-50',
    name: '曲马多 50mg',
    form: '胶囊',
    category: 'analgesic',
    class: '弱阿片类镇痛药',
    defaultDose: '1 cap, 3×1, PO',
    defaultDuration: '5 days',
    indications: [
      'hip-oa-moderate',
      'osteoarthritis-knee',
      'lumbar-disc-herniation',
      'meniscal-tear',
      'sciatica-l5',
    ],
    contraindications: [
      'mdd-moderate',
      'ptsd',
      'alcohol-use-disorder',
      'insomnia-chronic',
      'epilepsy',
    ],
  },
  {
    id: 'colchicine-05',
    name: '秋水仙碱 0.5mg',
    form: '片剂',
    category: 'analgesic',
    class: '抗痛风药',
    defaultDose: '1 tab,2-3×1, PO',
    defaultDuration: '7 days',
    indications: ['gout', 'pericarditis'],
    contraindications: ['ckd-stage3a'],
  },
  {
    id: 'allopurinol-300',
    name: '别嘌醇 300mg',
    form: '片剂',
    category: 'analgesic',
    class: '黄嘌呤氧化酶抑制剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['gout'],
  },

  // ─────────── PPIs / antacids / GI ───────────
  {
    id: 'pantoprazole-40',
    name: '泮托拉唑 40mg',
    form: '片剂',
    category: 'gastrointestinal',
    class: '质子泵抑制药 (PPI)',
    defaultDose: '1 tab, 1×1, PO (30 min before breakfast)',
    defaultDuration: '8 weeks',
    indications: [
      'gerd',
      'peptic-ulcer-disease',
      'laryngopharyngeal-reflux',
      'eosinophilic-esophagitis',
      'gerd-infant',
    ],
  },
  {
    id: 'esomeprazole-40',
    name: '埃索美拉唑 40mg',
    form: '片剂',
    category: 'gastrointestinal',
    class: '质子泵抑制药 (PPI)',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: '8 weeks',
    indications: ['gerd', 'peptic-ulcer-disease', 'laryngopharyngeal-reflux'],
  },
  {
    id: 'famotidine-40',
    name: '法莫替丁 40mg',
    form: '片剂',
    category: 'gastrointestinal',
    class: 'H2 受体拮抗药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: '4 weeks',
    indications: ['gerd', 'peptic-ulcer-disease'],
  },
  {
    id: 'loperamide-2',
    name: '洛哌丁胺 2mg',
    form: '胶囊',
    category: 'gastrointestinal',
    class: '阿片受体止泻药',
    defaultDose: '1-2 caps at onset, then 1 cap after each bowel movement',
    defaultDuration: '2 days',
    indications: ['viral-gastroenteritis', 'ibs-c'],
    contraindications: ['crohns-disease', 'ulcerative-colitis'],
  },
  {
    id: 'ondansetron-8',
    name: '昂丹司琼 8mg',
    form: '片剂',
    category: 'gastrointestinal',
    class: '5-HT3 受体拮抗药',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: '3 days',
    indications: ['viral-gastroenteritis', 'migraine-without-aura'],
  },
  {
    id: 'metoclopramide-10',
    name: '甲氧氯普胺 10mg',
    form: '片剂',
    category: 'gastrointestinal',
    class: '多巴胺拮抗止吐药',
    defaultDose: '1 tab, 3×1, PO',
    defaultDuration: '5 days',
    indications: ['viral-gastroenteritis', 'migraine-without-aura', 'gerd'],
    contraindications: ['idiopathic-parkinsons-early', 'essential-tremor'],
  },
  {
    id: 'lactulose-syrup',
    name: '乳果糖糖浆',
    form: '溶液',
    category: 'gastrointestinal',
    class: '渗透性泻药',
    defaultDose: '15 mL, 2×1, PO',
    defaultDuration: '14 days',
    indications: ['ibs-c', 'constipation-functional', 'hemorrhoids', 'hemorrhoids-grade2'],
  },
  {
    id: 'mesalazine-1g',
    name: '美沙拉嗪 1g',
    form: '片剂',
    category: 'gastrointestinal',
    class: '5-氨基水杨酸 (5-ASA)',
    defaultDose: '1 tab, 3×1, PO',
    defaultDuration: 'ongoing',
    indications: ['ulcerative-colitis', 'crohns-disease'],
  },

  // ─────────── Antihistamines ───────────
  {
    id: 'cetirizine-10',
    name: '西替利嗪 10mg',
    form: '片剂',
    category: 'allergy',
    class: '第二代 H1 抗组胺药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: '30 days',
    indications: [
      'allergic-rhinitis-seasonal',
      'allergic-rhinitis-ent',
      'allergic-rhinitis-asthma',
      'urticaria-chronic',
      'chronic-urticaria',
      'atopic-dermatitis',
      'atopic-dermatitis-child',
      'contact-dermatitis',
    ],
  },
  {
    id: 'levocetirizine-5',
    name: '左西替利嗪 5mg',
    form: '片剂',
    category: 'allergy',
    class: '第二代 H1 抗组胺药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: '30 days',
    indications: [
      'allergic-rhinitis-seasonal',
      'allergic-rhinitis-ent',
      'chronic-urticaria',
      'urticaria-chronic',
    ],
  },
  {
    id: 'desloratadine-5',
    name: '地氯雷他定 5mg',
    form: '片剂',
    category: 'allergy',
    class: '第二代 H1 抗组胺药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: '30 days',
    indications: ['allergic-rhinitis-seasonal', 'urticaria-chronic', 'chronic-urticaria'],
  },
  {
    id: 'fexofenadine-180',
    name: '非索非那定 180mg',
    form: '片剂',
    category: 'allergy',
    class: '第二代 H1 抗组胺药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: '30 days',
    indications: [
      'allergic-rhinitis-seasonal',
      'allergic-rhinitis-ent',
      'chronic-urticaria',
      'urticaria-chronic',
    ],
  },

  // ─────────── Asthma / COPD ───────────
  {
    id: 'salbutamol-inh',
    name: '沙丁胺醇吸入剂 100mcg',
    form: '喷雾剂',
    category: 'respiratory',
    class: '短效 β2 受体激动药',
    defaultDose: '2 puffs, as needed',
    defaultDuration: 'ongoing',
    indications: [
      'asthma-chronic',
      'asthma-allergic',
      'pediatric-asthma-exacerbation',
      'asthma-exacerbation',
      'copd-gold2',
      'chronic-bronchitis',
    ],
  },
  {
    id: 'budesonide-inh',
    name: '布地奈德吸入剂 200mcg',
    form: '喷雾剂',
    category: 'respiratory',
    class: '吸入性糖皮质激素',
    defaultDose: '2 puff, 2×1',
    defaultDuration: 'ongoing',
    indications: [
      'asthma-chronic',
      'asthma-allergic',
      'pediatric-asthma-exacerbation',
      'allergic-rhinitis-asthma',
    ],
  },
  {
    id: 'formoterol-budesonide-inh',
    name: '福莫特罗/布地奈德吸入剂',
    form: '喷雾剂',
    category: 'respiratory',
    class: '长效 β2 激动药 + 吸入糖皮质激素',
    defaultDose: '2 puff, 2×1',
    defaultDuration: 'ongoing',
    indications: ['asthma-chronic', 'asthma-allergic', 'copd-gold2'],
  },
  {
    id: 'tiotropium-inh',
    name: '噻托溴铵吸入剂 18mcg',
    form: '喷雾剂',
    category: 'respiratory',
    class: '长效抗胆碱能药 (LAMA)',
    defaultDose: '1 inh, 1×1',
    defaultDuration: 'ongoing',
    indications: ['copd-gold2', 'chronic-bronchitis'],
  },
  {
    id: 'montelukast-10',
    name: '孟鲁司特 10mg',
    form: '片剂',
    category: 'respiratory',
    class: '白三烯受体拮抗药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: [
      'asthma-chronic',
      'asthma-allergic',
      'allergic-rhinitis-asthma',
      'allergic-rhinitis-seasonal',
    ],
  },
  {
    id: 'fluticasone-nasal',
    name: '氟替卡松鼻喷雾剂',
    form: '喷雾剂',
    category: 'respiratory',
    class: '鼻用糖皮质激素',
    defaultDose: '2 puffs each nostril, 1×1',
    defaultDuration: 'ongoing',
    indications: [
      'allergic-rhinitis-seasonal',
      'allergic-rhinitis-ent',
      'allergic-rhinitis-asthma',
      'nasal-polyps',
      'chronic-rhinosinusitis',
    ],
  },

  // ─────────── Thyroid ───────────
  {
    id: 'levothyroxine-50',
    name: '左甲状腺素 50mcg',
    form: '片剂',
    category: 'endocrine',
    class: '甲状腺激素',
    defaultDose: '1 tab, 1×1, PO, on empty stomach',
    defaultDuration: 'ongoing',
    indications: ['hypothyroidism-hashimoto'],
    contraindications: ['graves-disease'],
  },
  {
    id: 'methimazole-5',
    name: '甲巯咪唑 5mg',
    form: '片剂',
    category: 'endocrine',
    class: '抗甲状腺药（硫酰胺类）',
    defaultDose: '2 tb, 3×1, PO',
    defaultDuration: '18 months',
    indications: ['graves-disease'],
    contraindications: ['hypothyroidism-hashimoto'],
  },
  {
    id: 'propylthiouracil-50',
    name: '丙硫氧嘧啶 50mg',
    form: '片剂',
    category: 'endocrine',
    class: '抗甲状腺药（硫酰胺类）',
    defaultDose: '2 tb, 3×1, PO',
    defaultDuration: '12 months',
    indications: ['graves-disease'],
    contraindications: ['hypothyroidism-hashimoto'],
  },

  // ─────────── Statins / Lipids ───────────
  {
    id: 'atorvastatin-20',
    name: '阿托伐他汀 20mg',
    form: '片剂',
    category: 'lipid-lowering',
    class: 'HMG-CoA 还原酶抑制剂（他汀类）',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: [
      'stable-angina',
      'type2-diabetes',
      'type2-dm-uncontrolled',
      'diabetic-nephropathy',
      'essential-hypertension',
      'ckd-stage3a',
    ],
    contraindications: ['statin-myalgia', 'chronic-hepatitis-b', 'chronic-hepatitis-c'],
  },
  {
    id: 'rosuvastatin-10',
    name: '瑞舒伐他汀 10mg',
    form: '片剂',
    category: 'lipid-lowering',
    class: 'HMG-CoA 还原酶抑制剂（他汀类）',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: ['stable-angina', 'type2-diabetes', 'essential-hypertension'],
    contraindications: ['statin-myalgia'],
  },
  {
    id: 'simvastatin-20',
    name: '辛伐他汀 20mg',
    form: '片剂',
    category: 'lipid-lowering',
    class: 'HMG-CoA 还原酶抑制剂（他汀类）',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: ['stable-angina', 'type2-diabetes'],
    contraindications: ['statin-myalgia'],
  },
  {
    id: 'ezetimibe-10',
    name: '依折麦布 10mg',
    form: '片剂',
    category: 'lipid-lowering',
    class: '胆固醇吸收抑制剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['stable-angina', 'statin-myalgia', 'type2-diabetes'],
  },

  // ─────────── Cardiology (other) ───────────
  {
    id: 'aspirin-100',
    name: '阿司匹林 100mg',
    form: '片剂',
    category: 'antiplatelet-anticoagulant',
    class: '抗血小板药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['stable-angina', 'stemi', 'ischemic-stroke', 'paroxysmal-afib'],
    contraindications: ['peptic-ulcer-disease', 'hemorrhagic-stroke', 'warfarin-bleeding-workup'],
  },
  {
    id: 'clopidogrel-75',
    name: '氯吡格雷 75mg',
    form: '片剂',
    category: 'antiplatelet-anticoagulant',
    class: '抗血小板药（P2Y12 抑制药）',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['stable-angina', 'stemi', 'ischemic-stroke'],
    contraindications: ['peptic-ulcer-disease', 'hemorrhagic-stroke'],
  },
  {
    id: 'apixaban-5',
    name: '阿哌沙班 5mg',
    form: '片剂',
    category: 'antiplatelet-anticoagulant',
    class: '直接口服抗凝药（Xa 抑制药）',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: 'ongoing',
    indications: ['paroxysmal-afib', 'dvt'],
    contraindications: ['peptic-ulcer-disease', 'hemorrhagic-stroke', 'warfarin-bleeding-workup'],
  },
  {
    id: 'nitroglycerin-sl',
    name: '硝酸甘油舌下含服 0.4mg',
    form: '喷雾剂',
    category: 'cardiovascular',
    class: '硝酸酯类',
    defaultDose: '1 puff sublingual, as needed',
    defaultDuration: 'ongoing',
    indications: ['stable-angina'],
  },
  {
    id: 'furosemide-40',
    name: '呋塞米 40mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '袢利尿药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['chf-nyha2', 'chf', 'pleural-effusion-parapneumonic'],
    contraindications: ['aki-pre-renal', 'orthostatic-hypotension'],
  },

  // ─────────── Antidepressants / anxiolytics ───────────
  {
    id: 'sertraline-50',
    name: '舍曲林 50mg',
    form: '片剂',
    category: 'psychiatry',
    class: 'SSRI 类抗抑郁药',
    defaultDose: '1 tab, 1×1, PO (morning)',
    defaultDuration: 'ongoing',
    indications: [
      'mdd-moderate',
      'generalized-anxiety',
      'panic-disorder',
      'ptsd',
      'ocd-moderate',
      'social-anxiety',
      'postpartum-depression',
    ],
    contraindications: ['bipolar-2-hypomanic', 'bipolar-1'],
  },
  {
    id: 'escitalopram-10',
    name: '艾司西酞普兰 10mg',
    form: '片剂',
    category: 'psychiatry',
    class: 'SSRI 类抗抑郁药',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'mdd-moderate',
      'generalized-anxiety',
      'panic-disorder',
      'social-anxiety',
      'menopause-vasomotor',
    ],
    contraindications: ['bipolar-2-hypomanic', 'bipolar-1'],
  },
  {
    id: 'fluoxetine-20',
    name: '氟西汀 20mg',
    form: '胶囊',
    category: 'psychiatry',
    class: 'SSRI 类抗抑郁药',
    defaultDose: '1 cap, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['mdd-moderate', 'ocd-moderate', 'panic-disorder'],
    contraindications: ['bipolar-2-hypomanic'],
  },
  {
    id: 'mirtazapine-30',
    name: '米氮平 30mg',
    form: '片剂',
    category: 'psychiatry',
    class: '非典型抗抑郁药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: ['mdd-moderate', 'insomnia-chronic'],
  },
  {
    id: 'lorazepam-1',
    name: '劳拉西泮 1mg',
    form: '片剂',
    category: 'psychiatry',
    class: '苯二氮䓬类',
    defaultDose: '1 tab, as needed (max 3×/day)',
    defaultDuration: '14 days',
    indications: ['generalized-anxiety', 'panic-disorder'],
    contraindications: [
      'alcohol-use-disorder',
      'obstructive-sleep-apnea',
      'insomnia-chronic',
      'copd-gold2',
    ],
  },
  {
    id: 'quetiapine-25',
    name: '喹硫平 25mg',
    form: '片剂',
    category: 'psychiatry',
    class: '非典型抗精神病药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: ['bipolar-2-hypomanic', 'bipolar-1'],
  },
  {
    id: 'methylphenidate-18',
    name: '哌甲酯缓释(OROS) 18mg',
    form: '片剂',
    category: 'psychiatry',
    class: '中枢兴奋药',
    defaultDose: '1 tab, morning, PO',
    defaultDuration: 'ongoing',
    indications: ['adhd-adult'],
    contraindications: ['generalized-anxiety', 'panic-disorder', 'insomnia-chronic'],
  },
  {
    id: 'zolpidem-10',
    name: '唑吡坦 10mg',
    form: '片剂',
    category: 'psychiatry',
    class: '非苯二氮䓬类催眠药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: '14 days',
    indications: ['insomnia-chronic'],
    contraindications: ['obstructive-sleep-apnea', 'alcohol-use-disorder'],
  },

  // ─────────── Migraine / Neuro ───────────
  {
    id: 'propranolol-40',
    name: '普萘洛尔 40mg',
    form: '片剂',
    category: 'cardiovascular',
    class: '非选择性 β-受体阻滞剂',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: 'ongoing',
    indications: ['migraine-without-aura', 'essential-tremor', 'graves-disease'],
    contraindications: ['asthma-chronic', 'asthma-allergic', 'copd-gold2'],
  },
  {
    id: 'topiramate-50',
    name: '托吡酯 50mg',
    form: '片剂',
    category: 'neurology',
    class: '抗癫痫 / 偏头痛预防药',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: 'ongoing',
    indications: ['migraine-without-aura', 'cluster-headache', 'epilepsy'],
    contraindications: ['nephrolithiasis-recurrent'],
  },
  {
    id: 'sumatriptan-50',
    name: '舒马普坦 50mg',
    form: '片剂',
    category: 'neurology',
    class: '5-HT1B/1D 受体激动药（曲普坦类）',
    defaultDose: '1 tab at onset',
    defaultDuration: 'as needed',
    indications: ['migraine-without-aura', 'cluster-headache'],
    contraindications: ['stable-angina', 'stemi', 'ischemic-stroke', 'htn-uncontrolled'],
  },
  {
    id: 'amitriptyline-25',
    name: '阿米替林 25mg',
    form: '片剂',
    category: 'neurology',
    class: '三环类抗抑郁药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: [
      'tension-headache',
      'migraine-without-aura',
      'fibromyalgia',
      'insomnia-chronic',
    ],
    contraindications: ['bph-moderate', 'primary-open-angle-glaucoma'],
  },
  {
    id: 'gabapentin-300',
    name: '加巴喷丁 300mg',
    form: '胶囊',
    category: 'neurology',
    class: '抗惊厥 / 神经性疼痛药',
    defaultDose: '1 cap, 3×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'sciatica-l5',
      'trigeminal-neuralgia',
      'carpal-tunnel',
      'lumbar-disc-herniation',
      'fibromyalgia',
      'shingles',
    ],
  },
  {
    id: 'carbamazepine-200',
    name: '卡马西平 200mg',
    form: '片剂',
    category: 'neurology',
    class: '抗惊厥药',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: 'ongoing',
    indications: ['trigeminal-neuralgia', 'epilepsy'],
  },
  {
    id: 'levodopa-carbidopa',
    name: '左旋多巴/卡比多巴 100/25',
    form: '片剂',
    category: 'neurology',
    class: '多巴胺前体药',
    defaultDose: '1 tab, 3×1, PO',
    defaultDuration: 'ongoing',
    indications: ['idiopathic-parkinsons-early'],
  },
  {
    id: 'donepezil-5',
    name: '多奈哌齐 5mg',
    form: '片剂',
    category: 'neurology',
    class: '胆碱酯酶抑制药',
    defaultDose: '1 tab, at night, PO',
    defaultDuration: 'ongoing',
    indications: ['mild-cognitive-impairment'],
  },
  {
    id: 'prednisone-burst',
    name: '泼尼松 1mg/kg',
    form: '片剂',
    category: 'endocrine',
    class: '全身用糖皮质激素',
    defaultDose: 'Gradual taper — start 60mg/day',
    defaultDuration: '10 days',
    indications: [
      'bells-palsy',
      'cluster-headache',
      'polymyalgia-rheumatica',
      'asthma-exacerbation',
      'pediatric-asthma-exacerbation',
      'sarcoidosis-stage2',
      'lupus-nephritis',
      'nephrotic-syndrome-membranous',
      'ulcerative-colitis',
      'crohns-disease',
      'sle',
    ],
    contraindications: ['peptic-ulcer-disease', 'type2-dm-uncontrolled'],
  },

  // ─────────── Dermatology ───────────
  {
    id: 'hydrocortisone-1-cr',
    name: '氢化可的松 1% 乳膏',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用糖皮质激素（弱效）',
    defaultDose: 'To affected area 2×/day',
    defaultDuration: '14 days',
    indications: [
      'atopic-dermatitis',
      'atopic-dermatitis-child',
      'contact-dermatitis',
      'seborrheic-dermatitis',
    ],
  },
  {
    id: 'mometasone-01-cr',
    name: '糠酸莫米松 0.1% 乳膏',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用糖皮质激素（中效）',
    defaultDose: 'To affected area 1×/day',
    defaultDuration: '14 days',
    indications: [
      'atopic-dermatitis',
      'contact-dermatitis',
      'plaque-psoriasis',
      'psoriasis-guttate',
      'alopecia-areata',
    ],
  },
  {
    id: 'clotrimazole-1-cr',
    name: '克霉唑 1% 乳膏',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用唑类抗真菌药',
    defaultDose: 'To affected area 2×/day',
    defaultDuration: '14 days',
    indications: ['tinea-corporis', 'candida-vulvovaginitis'],
  },
  {
    id: 'adapalene-01-gel',
    name: '阿达帕林 0.1% 凝胶',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用维 A 酸类',
    defaultDose: 'To face at night',
    defaultDuration: 'ongoing',
    indications: ['acne-vulgaris'],
    contraindications: ['normal-pregnancy-2nd-tri', 'gestational-dm'],
  },
  {
    id: 'benzoyl-peroxide-5',
    name: '过氧化苯甲酰 5% 凝胶',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用角质溶解药',
    defaultDose: 'To face at night',
    defaultDuration: 'ongoing',
    indications: ['acne-vulgaris'],
  },
  {
    id: 'metronidazole-gel',
    name: '甲硝唑 0.75% 凝胶',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用抗菌药',
    defaultDose: 'To affected area 2×/day',
    defaultDuration: '30 days',
    indications: ['rosacea'],
  },
  {
    id: 'tacrolimus-01-oint',
    name: '他克莫司 0.1% 软膏',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用钙调磷酸酶抑制药',
    defaultDose: 'To affected area 2×/day',
    defaultDuration: 'ongoing',
    indications: ['atopic-dermatitis', 'atopic-dermatitis-child'],
  },
  {
    id: 'calcipotriol-oint',
    name: '卡泊三醇软膏',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用维生素 D 类似物',
    defaultDose: 'To affected plaques 2×/day',
    defaultDuration: 'ongoing',
    indications: ['plaque-psoriasis', 'psoriasis-guttate'],
  },
  {
    id: 'permethrin-5-cream',
    name: '扑灭司林 5% 乳膏',
    form: '外用制剂',
    category: 'dermatology',
    class: '外用杀疥螨药',
    defaultDose: 'Whole body 8-14 hrs',
    defaultDuration: 'single dose',
    indications: ['scabies'],
  },
  {
    id: 'ketoconazole-shampoo',
    name: '酮康唑 2% 洗剂',
    form: '溶液',
    category: 'dermatology',
    class: '外用唑类抗真菌药',
    defaultDose: '2× per week',
    defaultDuration: 'ongoing',
    indications: ['seborrheic-dermatitis'],
  },

  // ─────────── Ophthalmic / ENT drops ───────────
  {
    id: 'timolol-eye-drops',
    name: '噻吗洛尔 0.5% 滴眼液',
    form: '溶液',
    category: 'ophthalmic',
    class: '外用 β-受体阻滞剂',
    defaultDose: '1 drop, 2×1, both eyes',
    defaultDuration: 'ongoing',
    indications: ['primary-open-angle-glaucoma'],
    contraindications: ['asthma-chronic', 'copd-gold2'],
  },
  {
    id: 'latanoprost-eye-drops',
    name: '拉坦前列素 0.005% 滴眼液',
    form: '溶液',
    category: 'ophthalmic',
    class: '前列腺素类似物',
    defaultDose: '1 drop, at night, both eyes',
    defaultDuration: 'ongoing',
    indications: ['primary-open-angle-glaucoma'],
  },
  {
    id: 'artificial-tears',
    name: '人工泪液',
    form: '溶液',
    category: 'ophthalmic',
    class: '人工泪液 / 眼润滑药',
    defaultDose: '1 drop, as needed',
    defaultDuration: 'ongoing',
    indications: ['dry-eye', 'blepharitis', 'sjogrens'],
  },

  // ─────────── Urology ───────────
  {
    id: 'tamsulosin-04',
    name: '坦索罗辛 0.4mg',
    form: '胶囊',
    category: 'urology',
    class: 'α1 肾上腺素能阻滞药',
    defaultDose: '1 cap, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['bph-moderate', 'kidney-stone-5mm', 'nephrolithiasis-recurrent'],
    contraindications: ['orthostatic-hypotension'],
  },
  {
    id: 'finasteride-5',
    name: '非那雄胺 5mg',
    form: '片剂',
    category: 'urology',
    class: '5α-还原酶抑制剂',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['bph-moderate'],
  },
  {
    id: 'sildenafil-50',
    name: '西地那非 50mg',
    form: '片剂',
    category: 'urology',
    class: 'PDE5 抑制药',
    defaultDose: '1 tab, 1 hr before intercourse',
    defaultDuration: 'as needed',
    indications: ['erectile-dysfunction-organic'],
    contraindications: ['stable-angina'],
  },
  {
    id: 'solifenacin-5',
    name: '索利那新 5mg',
    form: '片剂',
    category: 'urology',
    class: '抗胆碱能药（M3 选择性）',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['overactive-bladder'],
    contraindications: ['bph-moderate'],
  },

  // ─────────── Rheumatology / bone ───────────
  {
    id: 'methotrexate-15',
    name: '甲氨蝶呤 15mg',
    form: '片剂',
    category: 'rheumatology',
    class: '改善病情抗风湿药 (DMARD)',
    defaultDose: '1 tab, once weekly, PO',
    defaultDuration: 'ongoing',
    indications: [
      'rheumatoid-arthritis-early',
      'plaque-psoriasis',
      'crohns-disease',
      'ulcerative-colitis',
      'sle',
    ],
    contraindications: ['chronic-hepatitis-b', 'chronic-hepatitis-c'],
  },
  {
    id: 'hydroxychloroquine-200',
    name: '羟氯喹 200mg',
    form: '片剂',
    category: 'rheumatology',
    class: '抗疟类 DMARD',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: 'ongoing',
    indications: ['sle', 'rheumatoid-arthritis-early', 'sjogrens'],
  },
  {
    id: 'alendronate-70',
    name: '阿仑膦酸钠 70mg',
    form: '片剂',
    category: 'rheumatology',
    class: '双膦酸盐类',
    defaultDose: '1 tab, once weekly, on empty stomach',
    defaultDuration: 'ongoing',
    indications: ['osteoporosis-postmenopausal'],
    contraindications: ['gerd', 'peptic-ulcer-disease'],
  },
  {
    id: 'calcium-vitd',
    name: '钙 500 + 维生素 D3 1000IU',
    form: '片剂',
    category: 'hematology-nutrition',
    class: '矿物质 / 维生素',
    defaultDose: '1 tab, 2×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'osteoporosis-postmenopausal',
      'vit-d-deficiency',
      'hyperparathyroidism-primary',
    ],
  },

  // ─────────── Vitamins / hematinics ───────────
  {
    id: 'ferrous-sulfate-325',
    name: '硫酸亚铁 325mg',
    form: '片剂',
    category: 'hematology-nutrition',
    class: '口服铁剂',
    defaultDose: '1 tab, 1×1, PO (with vitamin C)',
    defaultDuration: '90 days',
    indications: [
      'iron-deficiency-anemia',
      'iron-deficiency',
      'iron-deficiency-infant',
      'thalassemia-trait',
    ],
    contraindications: ['hereditary-hemochromatosis'],
  },
  {
    id: 'vitamin-b12-im',
    name: '维生素 B12 1000mcg',
    form: '注射剂',
    category: 'hematology-nutrition',
    class: '钴胺素（维生素 B12）',
    defaultDose: '1 ampule IM, weekly',
    defaultDuration: '8 weeks',
    indications: ['b12-deficiency', 'b12-pernicious'],
  },
  {
    id: 'vitamin-d3-50k',
    name: '维生素 D3 50,000 IU',
    form: '胶囊',
    category: 'hematology-nutrition',
    class: '胆钙化醇（维生素 D3）',
    defaultDose: '1 cap, weekly, PO',
    defaultDuration: '8 weeks',
    indications: ['vit-d-deficiency', 'osteoporosis-postmenopausal'],
  },
  {
    id: 'folic-acid-5',
    name: '叶酸 5mg',
    form: '片剂',
    category: 'hematology-nutrition',
    class: '叶酸（维生素 B9）',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: [
      'b12-deficiency',
      'b12-pernicious',
      'iron-deficiency-anemia',
      'normal-pregnancy-2nd-tri',
      'thalassemia-trait',
    ],
  },
  {
    id: 'thiamine-100',
    name: '硫胺素 100mg',
    form: '片剂',
    category: 'hematology-nutrition',
    class: '硫胺素（维生素 B1）',
    defaultDose: '1 tab, 1×1, PO',
    defaultDuration: 'ongoing',
    indications: ['alcohol-use-disorder', 'chronic-fatigue'],
  },

  // ─────────── OB-GYN / menopause ───────────
  {
    id: 'combined-ocp',
    name: '复方口服避孕药',
    form: '片剂',
    category: 'obgyn',
    class: '雌激素 + 孕激素',
    defaultDose: '1 tab, 1×1, PO (28-day cycle)',
    defaultDuration: 'ongoing',
    indications: ['pcos', 'pcos-obgyn', 'endometriosis', 'menorrhagia-fibroids'],
    contraindications: ['normal-pregnancy-2nd-tri', 'dvt'],
  },
  {
    id: 'tranexamic-acid-500',
    name: '氨甲环酸 500mg',
    form: '片剂',
    category: 'obgyn',
    class: '抗纤溶药',
    defaultDose: '2 tab, 3×1, PO (during menses)',
    defaultDuration: '5 days',
    indications: ['menorrhagia-fibroids'],
    contraindications: ['dvt'],
  },
  {
    id: 'estradiol-patch',
    name: '雌二醇透皮 50mcg/日',
    form: '外用制剂',
    category: 'obgyn',
    class: '雌激素替代药',
    defaultDose: '1 patch, 2×/week',
    defaultDuration: 'ongoing',
    indications: ['menopause-vasomotor'],
    contraindications: ['normal-pregnancy-2nd-tri', 'dvt'],
  },
];

/* ------------------------------------------------------------------ */
/*  Lookups                                                            */
/* ------------------------------------------------------------------ */

const MED_BY_ID: Record<string, Medication> = Object.fromEntries(
  MEDICATIONS.map((m) => [m.id, m]),
);

export function medicationById(id: string): Medication | undefined {
  return MED_BY_ID[id];
}

/** All therapeutic classes currently represented, in the canonical catalog
 *  order. Useful for grouping the picker list. */
export function medicationClasses(): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const m of MEDICATIONS) {
    if (!seen.has(m.class)) {
      seen.add(m.class);
      out.push(m.class);
    }
  }
  return out;
}

/** Human-readable label for each high-level therapeutic category. */
export const CATEGORY_LABELS: Record<MedicationCategory, string> = {
  antibiotic: '抗生素',
  antiviral: '抗病毒药',
  antifungal: '抗真菌药',
  cardiovascular: '心血管药物',
  'antiplatelet-anticoagulant': '抗血小板 / 抗凝药',
  'lipid-lowering': '调脂药',
  endocrine: '内分泌与糖尿病用药',
  analgesic: '镇痛与 NSAID',
  gastrointestinal: '胃肠道用药',
  respiratory: '哮喘与慢阻肺用药',
  allergy: '过敏与抗组胺药',
  neurology: '神经科用药',
  psychiatry: '精神科用药',
  rheumatology: '风湿与骨骼用药',
  dermatology: '皮肤科用药',
  ophthalmic: '眼科用药',
  urology: '泌尿外科用药',
  obgyn: '妇产科用药',
  'hematology-nutrition': '血液与维生素',
};

/* ------------------------------------------------------------------ */
/*  Specialty scope — which therapeutic categories each polyclinic     */
/*  branch is allowed to prescribe from. Mirrors typical outpatient    */
/*  practice: internal medicine writes broadly, psychiatry writes      */
/*  psych drugs only, ophthalmology writes eye drops, etc.             */
/* ------------------------------------------------------------------ */

const ALL_CATEGORIES: MedicationCategory[] = [
  'antibiotic',
  'antiviral',
  'antifungal',
  'cardiovascular',
  'antiplatelet-anticoagulant',
  'lipid-lowering',
  'endocrine',
  'analgesic',
  'gastrointestinal',
  'respiratory',
  'allergy',
  'neurology',
  'psychiatry',
  'rheumatology',
  'dermatology',
  'ophthalmic',
  'urology',
  'obgyn',
  'hematology-nutrition',
];

export const SPECIALTY_MEDICATION_CATEGORIES: Record<ClinicId, MedicationCategory[]> = {
  'all-specialties': ALL_CATEGORIES,
  'internal-medicine': [
    'antibiotic', 'antiviral', 'antifungal', 'cardiovascular',
    'antiplatelet-anticoagulant', 'lipid-lowering', 'endocrine', 'analgesic',
    'gastrointestinal', 'respiratory', 'allergy', 'rheumatology', 'hematology-nutrition',
  ],
  cardiology: ['cardiovascular', 'antiplatelet-anticoagulant', 'lipid-lowering', 'analgesic'],
  neurology: ['neurology', 'analgesic', 'psychiatry'],
  neurosurgery: ['analgesic', 'antibiotic'],
  dermatology: ['dermatology', 'antifungal', 'antibiotic', 'allergy'],
  endocrinology: ['endocrine', 'lipid-lowering', 'cardiovascular', 'hematology-nutrition'],
  gastroenterology: ['gastrointestinal', 'antibiotic', 'analgesic'],
  pulmonology: ['respiratory', 'antibiotic', 'allergy', 'analgesic'],
  nephrology: ['cardiovascular', 'endocrine', 'hematology-nutrition', 'analgesic'],
  rheumatology: ['rheumatology', 'analgesic', 'antibiotic'],
  hematology: ['hematology-nutrition', 'antiplatelet-anticoagulant', 'antibiotic'],
  oncology: ['analgesic', 'antibiotic', 'antiviral', 'antifungal'],
  'infectious-disease': ['antibiotic', 'antiviral', 'antifungal'],
  'allergy-immunology': ['allergy', 'respiratory', 'dermatology'],
  psychiatry: ['psychiatry', 'neurology'],
  obgyn: ['obgyn', 'antibiotic', 'allergy', 'analgesic', 'hematology-nutrition'],
  urology: ['urology', 'antibiotic', 'analgesic'],
  ophthalmology: ['ophthalmic', 'antibiotic', 'allergy'],
  ent: ['antibiotic', 'allergy', 'analgesic', 'respiratory'],
  orthopedics: ['analgesic', 'rheumatology', 'antibiotic'],
  pmr: ['analgesic', 'rheumatology', 'neurology'],
  pediatrics: [
    'antibiotic', 'antiviral', 'respiratory', 'allergy',
    'gastrointestinal', 'analgesic', 'dermatology', 'hematology-nutrition',
  ],
  'general-surgery': ['antibiotic', 'analgesic', 'gastrointestinal', 'antiplatelet-anticoagulant'],
  'cardiothoracic-vascular-surgery': [
    'cardiovascular', 'antiplatelet-anticoagulant', 'antibiotic', 'analgesic', 'lipid-lowering',
  ],
};

export function isCategoryAllowedForSpecialty(
  category: MedicationCategory,
  specialty: ClinicId,
): boolean {
  return SPECIALTY_MEDICATION_CATEGORIES[specialty].includes(category);
}

/** Canonical display order for the top-level therapeutic categories. */
const CATEGORY_ORDER: MedicationCategory[] = [
  'antibiotic',
  'antiviral',
  'antifungal',
  'cardiovascular',
  'antiplatelet-anticoagulant',
  'lipid-lowering',
  'endocrine',
  'analgesic',
  'gastrointestinal',
  'respiratory',
  'allergy',
  'neurology',
  'psychiatry',
  'rheumatology',
  'dermatology',
  'ophthalmic',
  'urology',
  'obgyn',
  'hematology-nutrition',
];

/** Categories that actually appear in MEDICATIONS, in canonical display order. */
export function medicationCategories(): MedicationCategory[] {
  const present = new Set<MedicationCategory>(MEDICATIONS.map((m) => m.category));
  return CATEGORY_ORDER.filter((c) => present.has(c));
}

/** Suggest the single most specific drug for a diagnosis — used by the
 *  grader to tell the doctor what they missed if they submitted nothing. */
function suggestFor(diagnosisId: string): Medication | undefined {
  // Prefer drugs whose indications list this diagnosis AND which are NOT a
  // generic analgesic/antihistamine so we steer the user to specific Rx.
  const specific = MEDICATIONS.find(
    (m) =>
      m.indications.includes(diagnosisId) &&
      !['解热镇痛药', '非甾体抗炎药 (NSAID)', '第二代 H1 抗组胺药'].includes(m.class),
  );
  if (specific) return specific;
  return MEDICATIONS.find((m) => m.indications.includes(diagnosisId));
}

/* ------------------------------------------------------------------ */
/*  Grading                                                            */
/* ------------------------------------------------------------------ */

export interface PrescriptionGrade {
  /** Net points awarded / penalised. */
  score: number;
  /** Medication IDs that were clinically appropriate. */
  correct: string[];
  /** Medication IDs that were either contraindicated or unrelated. */
  wrong: string[];
  /** Human-readable suggestion of one key drug they should have prescribed. */
  missingSuggestion?: string;
  /** Human-readable feedback lines, one per point. */
  notes: string[];
}

/**
 * Grade a prescription:
 *   +30 per correctly-indicated drug (capped at +60)
 *   −20 per contraindicated drug
 *    −5 per unrelated drug (not indicated, not explicitly bad)
 *     0 if nothing prescribed (but mention what they missed)
 */
export function gradePrescription(
  diagnosisId: string,
  prescribedIds: string[],
): PrescriptionGrade {
  const correct: string[] = [];
  const wrong: string[] = [];
  const notes: string[] = [];

  // Deduplicate — if the user accidentally added the same drug twice, count
  // it once. Preserves the first-seen order.
  const unique: string[] = [];
  const seen = new Set<string>();
  for (const id of prescribedIds) {
    if (!seen.has(id)) {
      seen.add(id);
      unique.push(id);
    }
  }

  if (unique.length === 0) {
    const suggestion = suggestFor(diagnosisId);
    return {
      score: 0,
      correct: [],
      wrong: [],
      missingSuggestion: suggestion?.id,
      notes: suggestion
        ? [`未开具处方。针对本诊断可考虑 ${suggestion.name}。`]
        : ['未开具处方。本诊断亦无可适用药物。'],
    };
  }

  let correctCount = 0;
  let contraindicatedCount = 0;
  let unrelatedCount = 0;

  for (const id of unique) {
    const med = medicationById(id);
    if (!med) {
      // Unknown ID — treat as unrelated and note it.
      unrelatedCount += 1;
      wrong.push(id);
      notes.push(`未知药物 "${id}" —— 从治疗角度已被忽略。`);
      continue;
    }
    const isContraindicated = med.contraindications?.includes(diagnosisId) ?? false;
    const isIndicated = med.indications.includes(diagnosisId);

    if (isContraindicated) {
      contraindicatedCount += 1;
      wrong.push(id);
      notes.push(`⚠ ${med.name} 用于本诊断为禁忌。−20`);
    } else if (isIndicated) {
      correctCount += 1;
      correct.push(id);
      notes.push(`✓ ${med.name} —— 合理选择。+30`);
    } else {
      unrelatedCount += 1;
      wrong.push(id);
      notes.push(`~ ${med.name} 不用于本诊断。−5`);
    }
  }

  // Apply score with the +60 cap on correct credit.
  const correctPoints = Math.min(correctCount, 2) * 30;
  const contraPenalty = contraindicatedCount * 20;
  const unrelatedPenalty = unrelatedCount * 5;
  const score = correctPoints - contraPenalty - unrelatedPenalty;

  if (correctCount > 2) {
      notes.push(
        `(加分封顶：${correctCount} 种适宜药物，但仅前 2 种各计 +30。)`,
      );
  }

  // If they prescribed nothing correct, nudge them toward a canonical drug.
  let missingSuggestion: string | undefined;
  if (correctCount === 0) {
    const suggestion = suggestFor(diagnosisId);
    if (suggestion && !unique.includes(suggestion.id)) {
      missingSuggestion = suggestion.id;
      notes.push(`针对本诊断可考虑 ${suggestion.name}。`);
    }
  }

  return { score, correct, wrong, missingSuggestion, notes };
}
