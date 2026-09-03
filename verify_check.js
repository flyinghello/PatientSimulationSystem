import { PATIENT_CASES } from './src/data/patients.ts';
import { POLYCLINIC_CASES } from './src/data/polyclinicPatients.ts';
import { TESTS } from './src/data/tests.ts';
import { TREATMENTS } from './src/data/treatments.ts';
import { MEDICATIONS } from './src/data/medications.ts';

const testIds = new Set(TESTS.map(t => t.id));
const treatmentIds = new Set(TREATMENTS.map(t => t.id));

const allCases = [...PATIENT_CASES];
for (const [specialty, cases] of Object.entries(POLYCLINIC_CASES)) {
  if (specialty === 'all-specialties') continue;
  if (cases) allCases.push(...cases);
}

let violations = 0;
const caseIds = new Map();
const knownDiagnoses = new Set();

for (const c of allCases) {
  caseIds.set(c.id, (caseIds.get(c.id) ?? 0) + 1);
  knownDiagnoses.add(c.correctDiagnosisId);
  for (const opt of c.diagnosisOptions) knownDiagnoses.add(opt);

  for (const tr of c.testResults) {
    if (!testIds.has(tr.testId)) {
      console.log('VIOLATION: testResults.testId unknown in', c.id, ':', tr.testId);
      violations++;
    }
  }

  for (const tx of c.acceptableTreatmentIds) {
    if (!treatmentIds.has(tx)) {
      console.log('VIOLATION: acceptableTreatmentIds unknown in', c.id, ':', tx);
      violations++;
    }
  }
  for (const tx of c.criticalTreatmentIds) {
    if (!treatmentIds.has(tx)) {
      console.log('VIOLATION: criticalTreatmentIds unknown in', c.id, ':', tx);
      violations++;
    }
    if (!c.acceptableTreatmentIds.includes(tx)) {
      console.log('VIOLATION: critical not subset of acceptable in', c.id, ':', tx);
      violations++;
    }
  }

  if (!c.diagnosisOptions.includes(c.correctDiagnosisId)) {
    console.log('VIOLATION: correctDiagnosisId not in options in', c.id);
    violations++;
  }
}

for (const [id, count] of caseIds) {
  if (count > 1) {
    console.log('VIOLATION: duplicate case id', id, count);
    violations++;
  }
}

for (const med of MEDICATIONS) {
  for (const dx of med.indications ?? []) {
    if (!knownDiagnoses.has(dx)) {
      console.log('VIOLATION: medication indication unknown:', dx, 'in', med.id);
      violations++;
    }
  }
}

console.log('Total violations:', violations);