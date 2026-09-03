// Polyclinic (outpatient) specialty identifiers.
//
// These IDs key both patient rosters (`POLYCLINIC_CASES`) and UI labels.
// Kept in a separate module so the store, 3D scene, HUD view, and the
// patient-data file (owned by another agent) can all import from a
// single location without a circular dependency.

export type ClinicId =
  | 'all-specialties'
  | 'internal-medicine'
  | 'cardiology'
  | 'neurology'
  | 'neurosurgery'
  | 'dermatology'
  | 'endocrinology'
  | 'gastroenterology'
  | 'pulmonology'
  | 'nephrology'
  | 'rheumatology'
  | 'hematology'
  | 'oncology'
  | 'infectious-disease'
  | 'allergy-immunology'
  | 'psychiatry'
  | 'obgyn'
  | 'urology'
  | 'ophthalmology'
  | 'ent'
  | 'orthopedics'
  | 'pmr'
  | 'pediatrics'
  | 'general-surgery'
  | 'cardiothoracic-vascular-surgery';

/** Display order — also used by the specialty selector UI. The first entry
 *  is the "mixed" option that pulls cases from every specialty, so the
 *  doctor sees a rapid variety of demographics (kids, elderly, men, women)
 *  without having to switch clinics manually. */
export const CLINIC_IDS: ClinicId[] = [
  'all-specialties',
  'internal-medicine',
  'cardiology',
  'neurology',
  'neurosurgery',
  'dermatology',
  'endocrinology',
  'gastroenterology',
  'pulmonology',
  'nephrology',
  'rheumatology',
  'hematology',
  'oncology',
  'infectious-disease',
  'allergy-immunology',
  'psychiatry',
  'obgyn',
  'urology',
  'ophthalmology',
  'ent',
  'orthopedics',
  'pmr',
  'pediatrics',
  'general-surgery',
  'cardiothoracic-vascular-surgery',
];

/** 各专科的中文展示名称。 */
export const CLINIC_LABELS: Record<ClinicId, string> = {
  'all-specialties': '全部专科（混合）',
  'internal-medicine': '内科',
  cardiology: '心内科',
  neurology: '神经内科',
  neurosurgery: '神经外科',
  dermatology: '皮肤科',
  endocrinology: '内分泌科',
  gastroenterology: '消化内科',
  pulmonology: '呼吸内科',
  nephrology: '肾内科',
  rheumatology: '风湿免疫科',
  hematology: '血液内科',
  oncology: '肿瘤科',
  'infectious-disease': '感染科',
  'allergy-immunology': '过敏与免疫科',
  psychiatry: '精神科',
  obgyn: '妇产科',
  urology: '泌尿外科',
  ophthalmology: '眼科',
  ent: '耳鼻喉科',
  orthopedics: '骨科',
  pmr: '康复医学科',
  pediatrics: '儿科',
  'general-surgery': '普外科',
  'cardiothoracic-vascular-surgery': '心胸血管外科',
};

export const DEFAULT_CLINIC: ClinicId = 'internal-medicine';
