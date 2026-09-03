// Clinical practice guideline registry for the medkit-attending grading agent.
//
// Each entry is sourced directly from the publishing society's website
// (NICE, BTS, ESC, ADA, AHA, IDSA/ATS, etc.). Recommendation `text` fields
// are reproduced verbatim from the public guideline page; classification
// metadata (`recClass`, `lev`, GRADE) is only set when the source page
// explicitly states it.
//
// Every entry here is `verificationStatus: "auto-fetched"` until a
// clinician has reviewed the wording and confirmed accuracy. Do not flip
// any entry to `"verified"` from code — that is a human-MD sign-off only.
//
// `lastVerified` is the ISO date the page was retrieved by the curator
// agent (not necessarily the guideline publication date — see `year`).
//
// Citation format used by the grading agent:
//   `${guideline.id}:${rec.recId}`
// e.g. "nice-ng136-htn-2019:ng136-1.4.32-step1-acei-arb"

export interface GuidelineRecommendation {
  recId: string;
  text: string;
  recClass?: 'I' | 'IIa' | 'IIb' | 'III';
  lev?: 'A' | 'B' | 'C';
  gradeStrength?: 'strong' | 'conditional';
  gradeCertainty?: 'high' | 'moderate' | 'low' | 'very-low';
  topic: string;
  system:
    | 'cardiovascular'
    | 'endocrine'
    | 'respiratory'
    | 'renal'
    | 'gastrointestinal'
    | 'neurological'
    | 'musculoskeletal'
    | 'infectious'
    | 'other';
}

export interface Guideline {
  id: string;
  body:
    | 'NICE'
    | 'ESC'
    | 'ERS'
    | 'AHA'
    | 'ACC'
    | 'ADA'
    | 'BTS'
    | 'IDSA'
    | 'ATS'
    | 'GOLD'
    | 'GINA'
    | 'KDIGO'
    | 'ICH';
  year: number;
  region: 'UK' | 'EU' | 'US' | 'Global';
  title: string;
  url: string;
  pdfUrl?: string;
  doi?: string;
  pubmedId?: string;
  recommendations: GuidelineRecommendation[];
  verificationStatus: 'auto-fetched' | 'verified' | 'needs-verification';
  lastVerified: string;
  notes?: string;
  supersededBy?: string;
}

export const GUIDELINES: Guideline[] = [
  {
    id: 'nice-ng136-htn-2019',
    body: 'NICE',
    year: 2019,
    region: 'UK',
    title: 'Hypertension in adults: diagnosis and management (NG136)',
    url: 'https://www.nice.org.uk/guidance/ng136',
    pdfUrl:
      'https://www.nice.org.uk/guidance/ng136/resources/hypertension-in-adults-diagnosis-and-management-pdf-66141722710213',
    verificationStatus: 'auto-fetched',
    lastVerified: '2026-04-25',
    notes:
      'Originally published 28 August 2019; surveillance updates through February 2026 (postural hypotension Nov 2023, BP targets in CVD Mar 2022). Recommendation numbering taken from the live recommendations chapter on nice.org.uk.',
    recommendations: [
      {
        recId: 'ng136-1.2.8-diagnostic-threshold',
        text: 'Confirm diagnosis of hypertension in people with a: clinic blood pressure of 140/90 mmHg or higher and ABPM daytime average or HBPM average of 135/85 mmHg or higher.',
        topic: 'diagnostic threshold',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.4.1-lifestyle-advice',
        text: 'Offer lifestyle advice to people with suspected or diagnosed hypertension, and continue to offer it periodically.',
        topic: 'lifestyle intervention',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.4.10-stage1-under80-treatment',
        text: 'Discuss starting antihypertensive drug treatment, in addition to lifestyle advice, with adults aged under 80 with persistent stage 1 hypertension who have 1 or more of the following: target organ damage; established cardiovascular disease; renal disease; diabetes; an estimated 10-year risk of cardiovascular disease of 10% or more.',
        topic: 'when to start drug treatment',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.2.9-hbpm-technique',
        text: 'When assessing blood pressure with home blood pressure monitoring (HBPM), standardise technique: sit and rest for 5 minutes before measurement, support the bare arm at heart level, use an appropriately sized cuff, take two readings each morning and evening (ideally 1 minute apart) and record both values.',
        topic: 'home BP monitoring technique',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.4.32-step1-acei-arb',
        text: 'Offer an ACE inhibitor or an ARB to adults starting step 1 antihypertensive treatment who: have type 2 diabetes and are of any age or family origin, or are aged under 55 but not of Black African or African–Caribbean family origin.',
        topic: 'first-line drug choice',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.4.35-step1-ccb',
        text: 'Offer a calcium-channel blocker (CCB) to adults starting step 1 antihypertensive treatment who: are aged 55 or over and do not have type 2 diabetes, or are of Black African or African–Caribbean family origin and do not have type 2 diabetes (of any age).',
        topic: 'first-line drug choice',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.4.20-target-under80',
        text: 'For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level.',
        topic: 'blood pressure target',
        system: 'cardiovascular',
      },
      {
        recId: 'ng136-1.5.2-same-day-referral',
        text: 'Refer people for specialist assessment, carried out on the same day, if they have a clinic blood pressure of 180/120 mmHg and higher with: signs of retinal haemorrhage or papilloedema (accelerated hypertension) or life-threatening symptoms such as new onset confusion, chest pain, signs of heart failure, or acute kidney injury.',
        topic: 'red flag / same-day referral',
        system: 'cardiovascular',
      },
    ],
  },
  {
    id: 'nice-ng28-t2dm-2022',
    body: 'NICE',
    year: 2022,
    region: 'UK',
    title: 'Type 2 diabetes in adults: management (NG28)',
    url: 'https://www.nice.org.uk/guidance/ng28',
    pdfUrl:
      'https://www.nice.org.uk/guidance/ng28/resources/type-2-diabetes-in-adults-management-pdf-1837338615493',
    verificationStatus: 'auto-fetched',
    lastVerified: '2026-04-25',
    notes:
      'Originally published December 2015; major drug-treatment update February 2022 introducing the metformin + SGLT-2 inhibitor first-line pairing. Live recommendations chapter last touched 18 February 2026. Year retained as 2022 to reflect the substantive recommendation revision; consider bumping when NICE finalises the 2025/2026 draft.',
    recommendations: [
      {
        recId: 'ng28-1.2.1-structured-education',
        text: 'Offer structured education to adults with type 2 diabetes and their family members or carers (as appropriate) at the time of diagnosis, with annual reinforcement and review.',
        topic: 'structured education',
        system: 'endocrine',
      },
      {
        recId: 'ng28-1.3.3-healthy-eating',
        text: 'Encourage adults with type 2 diabetes to follow the same healthy eating advice as the general population, which includes: eating high-fibre, low-glycaemic-index sources of carbohydrate, such as fruit, vegetables, wholegrains and pulses; choosing low-fat dairy products; eating oily fish; controlling their intake of saturated and trans fatty acids.',
        topic: 'lifestyle / dietary advice',
        system: 'endocrine',
      },
      {
        recId: 'ng28-1.5.1-hba1c-monitoring',
        text: 'Measure HbA1c levels in adults with type 2 diabetes every: 3 to 6 months (tailored to individual needs) until HbA1c is stable on unchanging therapy; 6 months once the HbA1c level and blood glucose lowering therapy are stable.',
        topic: 'monitoring frequency',
        system: 'endocrine',
      },
      {
        recId: 'ng28-1.5.7-hba1c-target',
        text: 'For adults whose type 2 diabetes is managed either by healthy living and diet, or healthy living and diet combined with an initial medication regimen that is not associated with hypoglycaemia, support them to aim for an HbA1c level of 48 mmol/mol (6.5%). For adults on a medicine associated with hypoglycaemia, support them to aim for an HbA1c level of 53 mmol/mol (7.0%).',
        topic: 'glycaemic target',
        system: 'endocrine',
      },
      {
        recId: 'ng28-1.5.8-intensify-threshold',
        text: 'In adults with type 2 diabetes, if HbA1c levels are not adequately controlled by the initial medication regimen and rise to 58 mmol/mol (7.5%) or higher: reinforce advice about diet, healthy living and adherence to medicines and support the person to aim for an HbA1c level of 53 mmol/mol (7.0%) and intensify medicines.',
        topic: 'escalation threshold',
        system: 'endocrine',
      },
      {
        recId: 'ng28-1.13.1-initial-metformin-sglt2',
        text: 'For adults with type 2 diabetes and no relevant comorbidity, offer: modified-release metformin, and an SGLT-2 inhibitor.',
        topic: 'first-line pharmacotherapy',
        system: 'endocrine',
      },
      {
        recId: 'ng28-1.13.2-metformin-contraindicated',
        text: 'If metformin is contraindicated or not tolerated, offer monotherapy with an SGLT-2 inhibitor.',
        topic: 'first-line pharmacotherapy (alternative)',
        system: 'endocrine',
      },
    ],
  },
  {
    id: 'nice-ng250-pneumonia-2025',
    body: 'NICE',
    year: 2025,
    region: 'UK',
    title: 'Pneumonia: diagnosis and management (NG250)',
    url: 'https://www.nice.org.uk/guidance/ng250',
    verificationStatus: 'auto-fetched',
    lastVerified: '2026-04-25',
    notes:
      'Published 02 September 2025. Replaces the antimicrobial-prescribing guideline NG138 (2019) and incorporates portions of the older CG191 pathway. BTS 2009 CAP guideline remains the underlying evidence base but is not used here because the public BTS PDF was not machine-readable; once a clinician has reviewed BTS sections, add a `bts-cap-2009` entry alongside this one. Topics not covered here: hospital-acquired pneumonia (see NG139), and detailed empirical antibiotic agent/dose tables (recommendation 1.6.2 in NG250 references those tables rather than reproducing them inline).',
    recommendations: [
      {
        recId: 'ng250-1.2.1-crb65-community',
        text: 'If a clinical diagnosis of community-acquired pneumonia has been made, determine whether adults are at low, intermediate or high risk of death using the CRB65 scoring system.',
        topic: 'severity assessment (community)',
        system: 'respiratory',
      },
      {
        recId: 'ng250-1.2.7-curb65-hospital',
        text: 'If a clinical diagnosis of community-acquired pneumonia has been made in hospital, determine whether adults are at low, intermediate or high risk of death using the CURB65 scoring system.',
        topic: 'severity assessment (hospital)',
        system: 'respiratory',
      },
      {
        recId: 'ng250-1.5.1-start-antibiotics-4h',
        text: 'Start antibiotic treatment as soon as possible after establishing a diagnosis of community-acquired pneumonia, and within 4 hours of presentation to hospital.',
        topic: 'timing of antibiotic initiation',
        system: 'infectious',
      },
      {
        recId: 'ng250-1.5.4-oral-first-line',
        text: 'Give oral antibiotics first line if the person can take oral medicines, and the severity of their condition does not require intravenous antibiotics.',
        topic: 'route of administration',
        system: 'infectious',
      },
      {
        recId: 'ng250-1.5.5-iv-to-oral-switch',
        text: 'If intravenous antibiotics are given, review by 48 hours and, if possible, consider switching to oral antibiotics to complete the course.',
        topic: 'IV-to-oral switch',
        system: 'infectious',
      },
      {
        recId: 'ng250-1.6.3-stop-after-5-days',
        text: 'For adults with community-acquired pneumonia, stop antibiotic treatment after 5 days unless: microbiological results suggest a longer course is needed or the person is not clinically stable.',
        topic: 'duration of therapy',
        system: 'infectious',
      },
      {
        recId: 'ng250-1.10.3-safety-netting',
        text: 'Give advice to people with community-acquired pneumonia about possible adverse effects of the antibiotic(s); seeking further advice if symptoms worsen rapidly or significantly or do not start to improve within 3 days.',
        topic: 'safety-netting / follow-up',
        system: 'respiratory',
      },
      {
        recId: 'ng250-1.12.1-no-routine-fu-cxr',
        text: 'Do not routinely offer follow-up chest X-rays to people discharged from inpatient care after an episode of pneumonia.',
        topic: 'follow-up imaging',
        system: 'respiratory',
      },
    ],
  },
  {
    id: 'ich-e6-r2-2016',
    body: 'ICH',
    year: 2016,
    region: 'Global',
    title: 'Integrated Addendum to ICH E6(R1): Guideline for Good Clinical Practice E6(R2)',
    url: 'https://database.ich.org/sites/default/files/E6_R2_Addendum.pdf',
    verificationStatus: 'needs-verification',
    lastVerified: '2026-08-26',
    notes:
      'recIds follow the section numbering scheme chosen by the ct-001 case author (e.g. "4.2.3-subject-compliance"); wording below is a faithful paraphrase of the corresponding GCP investigator obligations, authored in-repo rather than fetched by the curator. A clinician should review the mapping before flipping this entry to "verified".',
    recommendations: [
      {
        recId: '4.2.3-subject-compliance',
        text: 'The investigator should explain to each subject the importance of taking the investigational product exactly as prescribed and of reporting dosing accurately (pill counts, diaries); any deviation from the intended dosing compliance should be documented and communicated to the sponsor.',
        topic: 'study-drug compliance / adherence monitoring',
        system: 'other',
      },
      {
        recId: '4.5.2-concomitant-therapy',
        text: 'The investigator should conduct the trial in compliance with the protocol, including its restrictions on concomitant medications; non-study medication use (including OTC and herbal products) must be documented, and protocol-required pre-approval obtained before the subject takes them.',
        topic: 'concomitant medication management',
        system: 'other',
      },
      {
        recId: '4.9.1-source-data-verification',
        text: 'The investigator should ensure the accuracy, completeness, legibility and timeliness of data reported to the sponsor; source records (including subject diaries) should be made at the time of the event and corrected entries must not obscure the original record.',
        topic: 'records and reports / source data',
        system: 'other',
      },
      {
        recId: '4.11.1-safety-reporting',
        text: 'All serious adverse events (SAEs) should be reported immediately to the sponsor except for those SAEs that the protocol or other document identifies as not needing immediate reporting; adverse events, even if mild or transient, should be reported per the protocol so the sponsor can conduct ongoing safety evaluation.',
        topic: 'safety reporting by the investigator',
        system: 'other',
      },
      {
        recId: '4.11.2-investigator-responsibilities',
        text: 'The investigator is responsible for the ongoing safety evaluation of trial subjects: subjects must be instructed to report any new symptoms or intercurrent events promptly and to contact the investigational site before changing study-drug administration or starting any new medication.',
        topic: 'investigator safety responsibilities / subject instructions',
        system: 'other',
      },
    ],
  },
];

export function getGuideline(id: string): Guideline | null {
  return GUIDELINES.find((g) => g.id === id) ?? null;
}

export function getRecommendation(
  ref: string,
): { guideline: Guideline; rec: GuidelineRecommendation } | null {
  // ref format: "guideline_id:rec_id"
  // e.g. "nice-ng136-htn-2019:ng136-1.4.32-step1-acei-arb"
  const [gid, rid] = ref.split(':');
  if (!gid || !rid) return null;
  const g = getGuideline(gid);
  if (!g) return null;
  const r = g.recommendations.find((x) => x.recId === rid);
  if (!r) return null;
  return { guideline: g, rec: r };
}
